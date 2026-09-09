"""
generate_raw_data.py
--------------------
Generates the four raw CSVs for the BrightBasket margin-leak project.

WHY THIS SCRIPT EXISTS (read this before an interview):
BrightBasket is a fictional D2C brand. No real company publishes order-level
COGS, shipping cost and RTO data together -- that combination is commercially
sensitive, so it does not exist as a public dataset. Rather than pretend, this
script builds a dataset with *explicitly stated* economics, sourced from
published Indian e-commerce benchmarks (see docs/ASSUMPTIONS.md). The point of
the project is the analytical method and the decision, not the discovery of a
secret fact about a real company.

The generator deliberately bakes in:
  1. A real causal structure (COD -> RTO, distance -> shipping cost,
     discount depth -> RTO, free-delivery threshold -> margin cliff)
  2. A confounder (one courier is disproportionately assigned tier-3 routes,
     so it looks bad on raw margin but is fine once you control for zone)
  3. Realistic data quality defects that must be cleaned with a stated reason

Run:  python scripts/generate_raw_data.py
Out:  data/raw/orders.csv, customers.csv, pincodes.csv, logistics.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path

RNG = np.random.default_rng(20260906)   # fixed seed => reproducible for reviewers
N_ORDERS = 40_000
OUT = Path(__file__).resolve().parents[1] / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------------
# 1. PINCODE MASTER
# ----------------------------------------------------------------------------
# Zones drive both shipping cost and COD propensity. This is the single most
# important dimension in the project, so it lives in its own table and is
# JOINed in -- exactly how a real warehouse-management system stores it.
CITIES = [
    # (city, state, zone, n_pincodes)
    ("Bengaluru",  "Karnataka",      "Metro", 14),
    ("Mumbai",     "Maharashtra",    "Metro", 14),
    ("Delhi",      "Delhi",          "Metro", 12),
    ("Hyderabad",  "Telangana",      "Metro", 10),
    ("Chennai",    "Tamil Nadu",     "Metro", 10),
    ("Pune",       "Maharashtra",    "Tier2", 8),
    ("Jaipur",     "Rajasthan",      "Tier2", 7),
    ("Lucknow",    "Uttar Pradesh",  "Tier2", 7),
    ("Kochi",      "Kerala",         "Tier2", 6),
    ("Indore",     "Madhya Pradesh", "Tier2", 6),
    ("Guwahati",   "Assam",          "Tier3", 6),
    ("Ranchi",     "Jharkhand",      "Tier3", 6),
    ("Siliguri",   "West Bengal",    "Tier3", 5),
    ("Gorakhpur",  "Uttar Pradesh",  "Tier3", 5),
    ("Bhagalpur",  "Bihar",          "Tier3", 5),
]

pin_rows, pin_seed = [], 110001
for city, state, zone, n in CITIES:
    for _ in range(n):
        pin_rows.append({"pincode": pin_seed, "city": city, "state": state, "zone": zone})
        pin_seed += 7
pincodes = pd.DataFrame(pin_rows)

# DATA QUALITY DEFECT #1: inconsistent city casing, as if two source systems
# wrote into the same table. Cleaning this is a one-liner but you must be able
# to say WHY it matters (it silently splits GROUP BY city into two rows).
casing = RNG.choice([0, 1, 2], size=len(pincodes), p=[0.72, 0.16, 0.12])
pincodes["city"] = [
    c if k == 0 else (c.upper() if k == 1 else c.lower())
    for c, k in zip(pincodes["city"], casing)
]

# ----------------------------------------------------------------------------
# 2. CUSTOMERS
# ----------------------------------------------------------------------------
N_CUST = 16_000
customers = pd.DataFrame({
    "customer_id": [f"C{100000+i}" for i in range(N_CUST)],
    "signup_date": pd.to_datetime("2024-10-01")
                   + pd.to_timedelta(RNG.integers(0, 500, N_CUST), unit="D"),
    "acquisition_channel": RNG.choice(
        ["Meta Ads", "Google Ads", "Organic", "Influencer", "Referral"],
        N_CUST, p=[0.34, 0.24, 0.18, 0.16, 0.08]),
})
customers["signup_date"] = customers["signup_date"].dt.strftime("%Y-%m-%d")

# ----------------------------------------------------------------------------
# 3. ORDERS
# ----------------------------------------------------------------------------
# Category economics. Gross margin % is the lever that decides whether an order
# can *absorb* a delivery cost at all. Staples at 18% cannot; skincare at 55% can.
CATEGORIES = {
    "Skincare":         dict(p=0.24, aov=820, sd=300, gm=0.55),
    "Haircare":         dict(p=0.21, aov=640, sd=240, gm=0.48),
    "Baby Care":        dict(p=0.14, aov=910, sd=330, gm=0.38),
    "Home Cleaning":    dict(p=0.22, aov=545, sd=210, gm=0.28),
    "Household Staples":dict(p=0.19, aov=470, sd=170, gm=0.18),
}
cat_names = list(CATEGORIES)
cat_probs = [CATEGORIES[c]["p"] for c in cat_names]

order_ids   = [f"BB{500000+i}" for i in range(N_ORDERS)]
cust_ids    = RNG.choice(customers["customer_id"], N_ORDERS,
                         p=(w := RNG.dirichlet(np.full(N_CUST, 1.4))) / w.sum())
dates       = pd.to_datetime("2025-04-01") + pd.to_timedelta(RNG.integers(0, 365, N_ORDERS), unit="D")
category    = RNG.choice(cat_names, N_ORDERS, p=cat_probs)

# Zone mix: 55% metro / 30% tier2 / 15% tier3, matching a typical D2C footprint
zone_choice = RNG.choice(["Metro", "Tier2", "Tier3"], N_ORDERS, p=[0.55, 0.30, 0.15])
pin_by_zone = {z: pincodes.loc[pincodes.zone == z, "pincode"].to_numpy() for z in ["Metro", "Tier2", "Tier3"]}
pincode_col = np.array([RNG.choice(pin_by_zone[z]) for z in zone_choice])

# Order value: lognormal-ish around the category AOV, floored at Rs 149
aov = np.array([CATEGORIES[c]["aov"] for c in category], dtype=float)
sd  = np.array([CATEGORIES[c]["sd"]  for c in category], dtype=float)
gross_value = np.maximum(RNG.normal(aov, sd), 149).round(0)

# Discounts: most orders 0-15%, a promo-heavy tail up to 45%.
disc_pct = np.clip(RNG.beta(1.7, 7.0, N_ORDERS) * 0.62, 0, 0.45)
discount = (gross_value * disc_pct).round(0)
net_value = gross_value - discount

# COGS from category gross margin, with +/- noise for supplier/batch variation
gm = np.array([CATEGORIES[c]["gm"] for c in category])
product_cost = (gross_value * (1 - np.clip(gm + RNG.normal(0, 0.035, N_ORDERS), 0.08, 0.72))).round(0)

# PAYMENT MODE -- the core driver. COD share rises sharply outside metros
# because card/UPI trust and connectivity are lower. This is the real-world
# pattern the whole project hangs on.
cod_prob = np.select([zone_choice == "Metro", zone_choice == "Tier2"], [0.46, 0.66], default=0.79)
payment_mode = np.where(RNG.random(N_ORDERS) < cod_prob, "COD", "Prepaid")

# FREE DELIVERY THRESHOLD = Rs 499 on NET value. Below it we charge Rs 49.
# This is the policy under review; the margin cliff it creates is finding #3.
FREE_DELIVERY_THRESHOLD = 499
delivery_fee_charged = np.where(net_value < FREE_DELIVERY_THRESHOLD, 49.0, 0.0)

# ORDER STATUS: Delivered / RTO / Cancelled.
# RTO (Return To Origin) = customer refuses or is unreachable; we pay shipping
# both ways and collect nothing. Base rates from published Indian D2C benchmarks.
rto_rate = np.where(payment_mode == "COD", 0.070, 0.018)
rto_rate = rto_rate + np.where((payment_mode == "COD") & (zone_choice == "Tier3"), 0.085, 0.0)
rto_rate = rto_rate + np.where((payment_mode == "COD") & (zone_choice == "Tier2"), 0.022, 0.0)
rto_rate = rto_rate + np.where(disc_pct > 0.25, 0.030, 0.0)          # discount-hunters bail
rto_rate = rto_rate + np.where((payment_mode == "COD") & (net_value < 600), 0.020, 0.0)
rto_rate = np.clip(rto_rate, 0.005, 0.32)

roll = RNG.random(N_ORDERS)
status = np.where(roll < rto_rate, "RTO",
          np.where(roll < rto_rate + 0.028, "Cancelled", "Delivered"))

orders = pd.DataFrame({
    "order_id": order_ids,
    "customer_id": cust_ids,
    "order_date": dates.strftime("%Y-%m-%d"),
    "pincode": pincode_col,
    "category": category,
    "payment_mode": payment_mode,
    "gross_order_value": gross_value,
    "discount_amount": discount,
    "delivery_fee_charged": delivery_fee_charged,
    "product_cost": product_cost,
    "order_status": status,
})

# ----------------------------------------------------------------------------
# 4. LOGISTICS  (separate table -- the 3PL bills us on its own file)
# ----------------------------------------------------------------------------
# Forward cost rises with distance. RTO leg costs ~1.55x forward (return
# freight + two handling touches). These are cost TO US, not fee charged.
base_ship = np.select(
    [zone_choice == "Metro", zone_choice == "Tier2"],
    [RNG.normal(64, 8, N_ORDERS), RNG.normal(88, 11, N_ORDERS)],
    default=RNG.normal(118, 16, N_ORDERS)).round(0)
base_ship = np.clip(base_ship, 38, None)

# COURIER ASSIGNMENT -- the deliberate confounder.
# BharatShip takes the bulk of tier-3 volume (they are the only ones with that
# reach). Raw margin-per-order will therefore make BharatShip look terrible.
# Within tier 3 they are actually marginally BETTER on RTO. Anyone who reads
# the raw cut and says "drop BharatShip" is wrong, and that is the trap.
courier = np.empty(N_ORDERS, dtype=object)
for z, probs in {
    "Metro": [0.55, 0.12, 0.33],
    "Tier2": [0.33, 0.40, 0.27],
    "Tier3": [0.10, 0.78, 0.12],
}.items():
    m = zone_choice == z
    courier[m] = RNG.choice(["SwiftLogix", "BharatShip", "ZipEx"], m.sum(), p=probs)

forward_cost = np.where(status == "Cancelled", 0.0, base_ship)
rto_cost = np.where(status == "RTO", (base_ship * 1.55).round(0), 0.0)
attempts = np.where(status == "RTO", RNG.integers(2, 4, N_ORDERS),
            np.where(status == "Cancelled", 0, RNG.choice([1, 2], N_ORDERS, p=[0.88, 0.12])))

logistics = pd.DataFrame({
    "order_id": order_ids,
    "courier_partner": courier,
    "forward_shipping_cost": forward_cost,
    "rto_shipping_cost": rto_cost,
    "delivery_attempts": attempts,
})

# ----------------------------------------------------------------------------
# 5. INJECT DATA QUALITY DEFECTS
# ----------------------------------------------------------------------------
# Every defect below is one you must be able to detect, justify fixing, and
# state the impact of. They are not noise -- they are the cleaning section of
# the project.

# #2 Duplicate order rows (a real failure mode: an ETL job re-ran and appended)
dupe_idx = RNG.choice(N_ORDERS, 180, replace=False)
orders = pd.concat([orders, orders.iloc[dupe_idx]], ignore_index=True)

# #3 Missing pincodes (~1.5%) -- address parser failed on free-text entry
miss = RNG.choice(orders.index, int(len(orders) * 0.015), replace=False)
orders.loc[miss, "pincode"] = np.nan

# #4 Mixed date formats -- one upstream system writes DD-MM-YYYY
fmt_idx = RNG.choice(orders.index, 900, replace=False)
orders.loc[fmt_idx, "order_date"] = pd.to_datetime(
    orders.loc[fmt_idx, "order_date"]).dt.strftime("%d-%m-%Y")

# #5 Negative discounts -- post-hoc refund adjustments booked to the wrong field
neg_idx = RNG.choice(orders.index, 120, replace=False)
orders.loc[neg_idx, "discount_amount"] = -orders.loc[neg_idx, "discount_amount"].abs()

# #6 Internal test orders with zero value
test_idx = RNG.choice(orders.index, 45, replace=False)
orders.loc[test_idx, "gross_order_value"] = 0
orders.loc[test_idx, "product_cost"] = 0
orders.loc[test_idx, "customer_id"] = "INTERNAL_QA"

# #7 Cancelled orders carrying phantom shipping cost (3PL billed in error)
canc = orders.loc[orders.order_status == "Cancelled", "order_id"].head(140)
logistics.loc[logistics.order_id.isin(canc), "forward_shipping_cost"] = 55.0

orders = orders.sample(frac=1, random_state=7).reset_index(drop=True)

# ----------------------------------------------------------------------------
orders.to_csv(OUT / "orders.csv", index=False)
customers.to_csv(OUT / "customers.csv", index=False)
pincodes.to_csv(OUT / "pincodes.csv", index=False)
logistics.to_csv(OUT / "logistics.csv", index=False)

print(f"orders     {orders.shape}")
print(f"customers  {customers.shape}")
print(f"pincodes   {pincodes.shape}")
print(f"logistics  {logistics.shape}")
print("\nstatus mix:\n", orders.order_status.value_counts(normalize=True).round(4))
print("\npayment mix:\n", orders.payment_mode.value_counts(normalize=True).round(4))
