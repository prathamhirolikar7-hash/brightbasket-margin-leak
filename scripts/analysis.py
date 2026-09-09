"""
analysis.py -- cleaning + the six analysis questions, end to end.
Mirrors notebooks/01_cleaning_and_analysis.ipynb. Prints every number that
appears in README.md, so the repo can never drift from the numbers.
"""
import numpy as np, pandas as pd, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)
pd.set_option("display.width", 200, "display.max_columns", 40)
R = {}   # results dict -> written to docs/key_numbers.json

orders    = pd.read_csv(RAW / "orders.csv")
customers = pd.read_csv(RAW / "customers.csv")
pincodes  = pd.read_csv(RAW / "pincodes.csv")
logistics = pd.read_csv(RAW / "logistics.csv")

print("=" * 78); print("STEP 1 — DATA QUALITY AUDIT (count before you fix)"); print("=" * 78)
R["rows_raw"] = len(orders)
R["dupes"] = int(orders.order_id.duplicated().sum())
R["missing_pincode"] = int(orders.pincode.isna().sum())
R["neg_discount"] = int((orders.discount_amount < 0).sum())
R["zero_value"] = int((orders.gross_order_value == 0).sum())
R["cancelled"] = int((orders.order_status == "Cancelled").sum())
for k in ["rows_raw", "dupes", "missing_pincode", "neg_discount", "zero_value", "cancelled"]:
    print(f"  {k:20s} {R[k]:>7,}")

print("\n" + "=" * 78); print("STEP 2 — CLEANING"); print("=" * 78)
# 2a. drop exact duplicate order_ids — keep first. An order_id is the grain of
#     the table; two rows with the same id double-count revenue AND cost.
orders = orders.drop_duplicates(subset="order_id", keep="first")

# 2b. mixed date formats -> single datetime. format="mixed" lets pandas parse
#     both YYYY-MM-DD and DD-MM-YYYY per row instead of silently coercing.
orders["order_date"] = pd.to_datetime(orders.order_date, format="mixed", dayfirst=True)

# 2c. negative discounts -> absolute value. A discount is a magnitude; the sign
#     is a booking error. Flagged, not deleted, so the count is auditable.
orders["discount_flag_fixed"] = orders.discount_amount < 0
orders["discount_amount"] = orders.discount_amount.abs()

# 2d. remove internal QA orders — zero revenue, zero cost, not real demand.
orders = orders[orders.customer_id != "INTERNAL_QA"]

# 2e. drop rows with no pincode. Zone is the primary analysis dimension; an
#     order with no zone cannot be assigned to any recommendation. 1.5% is
#     small and (checked below) not concentrated in one segment.
lost = orders.pincode.isna()
R["dropped_no_pincode_pct"] = round(100 * lost.mean(), 2)
R["missing_bias_check"] = orders.loc[lost, "payment_mode"].value_counts(normalize=True).round(3).to_dict()
print("  missing-pincode payment mix (bias check):", R["missing_bias_check"])
orders = orders[~lost].copy()
orders["pincode"] = orders.pincode.astype(int)

# 2f. standardise city casing BEFORE any GROUP BY city
pincodes["city"] = pincodes.city.str.strip().str.title()

# 2g. phantom shipping on cancelled orders -> 0. We never shipped it.
df = (orders
      .merge(pincodes, on="pincode", how="left")
      .merge(logistics, on="order_id", how="left")
      .merge(customers, on="customer_id", how="left"))
phantom = (df.order_status == "Cancelled") & (df.forward_shipping_cost > 0)
R["phantom_shipping_rows"] = int(phantom.sum())
df.loc[phantom, "forward_shipping_cost"] = 0.0
print(f"  phantom shipping rows zeroed: {R['phantom_shipping_rows']}")
R["rows_clean"] = len(df)
print(f"  rows: {R['rows_raw']:,} raw -> {R['rows_clean']:,} clean "
      f"({100*R['rows_clean']/R['rows_raw']:.1f}% retained)")

print("\n" + "=" * 78); print("STEP 3 — BUILD THE CONTRIBUTION MARGIN"); print("=" * 78)
COD_FEE, PG_RATE, RTO_WRITEOFF = 25.0, 0.02, 0.15
# net_order_value = what the order was WORTH (exists for every order, any status)
# net_revenue     = what we actually COLLECTED (zero unless delivered)
# Keeping these separate matters: banding orders by "revenue" would silently
# push every RTO into the <300 bucket and corrupt the whole value analysis.
df["net_order_value"] = df.gross_order_value - df.discount_amount
df["net_revenue"] = np.where(df.order_status == "Delivered", df.net_order_value, 0.0)
df["delivery_revenue"] = np.where(df.order_status == "Delivered", df.delivery_fee_charged, 0.0)
df["cogs_effective"] = np.select(
    [df.order_status == "Delivered", df.order_status == "RTO"],
    [df.product_cost, df.product_cost * RTO_WRITEOFF], default=0.0)
df["shipping_cost"] = df.forward_shipping_cost.fillna(0) + df.rto_shipping_cost.fillna(0)
df["payment_cost"] = np.where(
    (df.order_status == "Delivered") & (df.payment_mode == "COD"), COD_FEE,
    np.where((df.order_status == "Delivered") & (df.payment_mode == "Prepaid"),
             (df.net_revenue + df.delivery_revenue) * PG_RATE, 0.0)).round(2)
df["contribution_margin"] = (df.net_revenue + df.delivery_revenue
                             - df.cogs_effective - df.shipping_cost - df.payment_cost).round(2)
df["is_loss"] = df.contribution_margin < 0
df["value_band"] = pd.cut(df.net_order_value,
                          [-1, 299, 499, 699, 999, 1e9],
                          labels=["Under 300", "300-499", "500-699", "700-999", "1000+"])

print("\n" + "=" * 78); print("Q1 — HOW BIG IS THE LEAK?"); print("=" * 78)
R["total_revenue"] = round(float((df.net_revenue + df.delivery_revenue).sum()))
R["total_cm"] = round(float(df.contribution_margin.sum()))
R["cm_pct"] = round(100 * R["total_cm"] / R["total_revenue"], 1)
R["loss_orders"] = int(df.is_loss.sum())
R["loss_order_pct"] = round(100 * df.is_loss.mean(), 1)
R["loss_value"] = round(float(df.loc[df.is_loss, "contribution_margin"].sum()))
R["profit_value"] = round(float(df.loc[~df.is_loss, "contribution_margin"].sum()))
R["leak_as_pct_of_profit"] = round(100 * abs(R["loss_value"]) / R["profit_value"], 1)
print(f"  revenue Rs {R['total_revenue']:,}   CM Rs {R['total_cm']:,} ({R['cm_pct']}%)")
print(f"  loss-making orders: {R['loss_orders']:,} ({R['loss_order_pct']}%) "
      f"burning Rs {abs(R['loss_value']):,}")
print(f"  => the leak destroys {R['leak_as_pct_of_profit']}% of gross contribution")

print("\n" + "=" * 78); print("Q2 — WHERE IS IT? (payment x zone)"); print("=" * 78)
seg = (df.groupby(["zone", "payment_mode"], observed=True)
         .agg(orders=("order_id", "count"),
              rto_rate=("order_status", lambda s: round(100*(s == "RTO").mean(), 1)),
              cm_total=("contribution_margin", "sum"),
              cm_per_order=("contribution_margin", "mean"))
         .round(1).reset_index().sort_values("cm_per_order"))
print(seg.to_string(index=False))
R["segments"] = seg.to_dict("records")

print("\n" + "=" * 78); print("Q3 — IS IT COD, OR IS IT DISTANCE? (controlled cut)"); print("=" * 78)
pm = df.groupby("payment_mode", observed=True).contribution_margin.agg(["count", "mean"]).round(1)
print("  Naive cut (payment only):"); print(pm.to_string())
R["cod_cm_per_order"] = round(float(pm.loc["COD", "mean"]), 1)
R["prepaid_cm_per_order"] = round(float(pm.loc["Prepaid", "mean"]), 1)
cod_metro = df[(df.payment_mode == "COD") & (df.zone == "Metro")].contribution_margin.mean()
cod_t3 = df[(df.payment_mode == "COD") & (df.zone == "Tier3")].contribution_margin.mean()
R["cod_metro_cm"] = round(float(cod_metro), 1)
R["cod_tier3_cm"] = round(float(cod_t3), 1)
print(f"\n  COD in Metro: Rs {R['cod_metro_cm']}/order   COD in Tier3: Rs {R['cod_tier3_cm']}/order")
print("  => 'COD is bad' is false. COD in metro is profitable. The problem is COD x Tier3.")

print("\n" + "=" * 78); print("Q4 — THE COURIER RED HERRING"); print("=" * 78)
raw_c = df.groupby("courier_partner", observed=True).contribution_margin.mean().round(1)
print("  Raw margin per order by courier:"); print(raw_c.to_string())
ctrl = (df.pivot_table(index="courier_partner", columns="zone",
                       values="contribution_margin", aggfunc="mean").round(1))
print("\n  Same thing, controlled for zone:"); print(ctrl.to_string())
mix = (df.pivot_table(index="courier_partner", columns="zone",
                      values="order_id", aggfunc="count", fill_value=0))
mix_pct = (100 * mix.div(mix.sum(axis=1), axis=0)).round(1)
print("\n  Volume mix % (the explanation):"); print(mix_pct.to_string())
R["courier_raw"] = raw_c.to_dict()
R["courier_controlled"] = ctrl.round(1).to_dict()
R["courier_mix_pct"] = mix_pct.to_dict()
R["bharatship_tier3_share"] = float(mix_pct.loc["BharatShip", "Tier3"])

print("\n" + "=" * 78); print("Q5 — THE FREE-DELIVERY CLIFF (threshold = Rs 499)"); print("=" * 78)
band = (df.groupby("value_band", observed=True)
          .agg(orders=("order_id", "count"),
               avg_delivery_fee=("delivery_revenue", "mean"),
               avg_shipping_cost=("shipping_cost", "mean"),
               cm_per_order=("contribution_margin", "mean"),
               cm_total=("contribution_margin", "sum")).round(1))
print(band.to_string())
R["band"] = band.reset_index().astype({"value_band": str}).to_dict("records")
cliff = df[df.net_order_value.between(500, 699)]
R["cliff_orders"] = int(len(cliff))
R["cliff_cm"] = round(float(cliff.contribution_margin.mean()), 1)
print(f"\n  Orders Rs 500-699 (just past the free-delivery line): {R['cliff_orders']:,} "
      f"at Rs {R['cliff_cm']}/order")

print("\n" + "=" * 78); print("Q6 — SIZING THE FIX"); print("=" * 78)
# Target = the specific pocket, not a blanket ban.
target = df[(df.payment_mode == "COD") & (df.zone == "Tier3") & (df.net_order_value < 700)]
R["target_orders"] = int(len(target))
R["target_share_pct"] = round(100 * len(target) / len(df), 1)
R["target_cm"] = round(float(target.contribution_margin.sum()))
R["target_cm_per_order"] = round(float(target.contribution_margin.mean()), 1)
R["target_rto"] = round(100 * float((target.order_status == "RTO").mean()), 1)
print(f"  Target pocket: COD + Tier3 + net value < Rs 700")
print(f"    {R['target_orders']:,} orders ({R['target_share_pct']}% of volume), "
      f"RTO {R['target_rto']}%, CM Rs {R['target_cm']:,} (Rs {R['target_cm_per_order']}/order)")

# Scenario: force prepaid in that pocket. Stated assumption -> 35% convert.
CONVERT = 0.35
prep_t3 = df[(df.payment_mode == "Prepaid") & (df.zone == "Tier3") & (df.net_order_value < 700)]
R["prepaid_analogue_cm_per_order"] = round(float(prep_t3.contribution_margin.mean()), 1)
recovered = R["target_orders"] * CONVERT * R["prepaid_analogue_cm_per_order"]
avoided = -R["target_cm"]
R["scenario_convert_rate"] = CONVERT
R["scenario_net_gain"] = round(float(avoided + recovered))
R["scenario_revenue_at_risk"] = round(float(
    target.net_order_value.sum() * (1 - CONVERT)))
print(f"\n  If we make this pocket prepaid-only, assuming {int(CONVERT*100)}% convert:")
print(f"    losses avoided      Rs {avoided:>12,.0f}")
print(f"    margin from converts Rs {recovered:>11,.0f}  "
      f"(at Rs {R['prepaid_analogue_cm_per_order']}/order, the observed prepaid analogue)")
print(f"    NET GAIN            Rs {R['scenario_net_gain']:>12,.0f}")
print(f"    revenue given up    Rs {R['scenario_revenue_at_risk']:>12,.0f}")

# Second lever: raise free-delivery threshold 499 -> 699
below = df[df.net_order_value.between(500, 698) & (df.order_status == "Delivered")]
R["lever2_orders"] = int(len(below))
R["lever2_fee_gain"] = round(float(len(below) * 49 * 0.75))   # 25% assumed to drop out
R["combined_annual_gain"] = R["scenario_net_gain"] + R["lever2_fee_gain"]
print(f"\n  Lever 2 — threshold Rs 499 -> Rs 699: {R['lever2_orders']:,} orders would now pay "
      f"Rs 49; at 75% retention that is Rs {R['lever2_fee_gain']:,}")
print(f"\n  COMBINED ANNUAL RECOVERY: Rs {R['combined_annual_gain']:,} "
      f"({round(100*R['combined_annual_gain']/R['total_cm'],1)}% lift on current CM)")

# ---------------------------------------------------------------- exports
keep = ["order_id", "order_date", "customer_id", "city", "state", "zone", "pincode",
        "category", "payment_mode", "courier_partner", "acquisition_channel",
        "order_status", "gross_order_value", "discount_amount", "delivery_fee_charged",
        "product_cost", "forward_shipping_cost", "rto_shipping_cost", "net_order_value", "net_revenue",
        "delivery_revenue", "cogs_effective", "shipping_cost", "payment_cost",
        "contribution_margin", "is_loss", "value_band"]
df[keep].to_csv(PROC / "order_economics.csv", index=False)
seg.to_csv(PROC / "summary_zone_payment.csv", index=False)
band.reset_index().to_csv(PROC / "summary_value_band.csv", index=False)
(ROOT / "docs").mkdir(exist_ok=True)
json.dump(R, open(ROOT / "docs" / "key_numbers.json", "w"), indent=2, default=str)
print(f"\n[exported] data/processed/order_economics.csv  ({len(df):,} rows)")
