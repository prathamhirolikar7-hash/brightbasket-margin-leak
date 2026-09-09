"""Builds notebooks/01_cleaning_and_analysis.ipynb from structured cells."""
import json
from pathlib import Path

def md(t):   return {"cell_type": "markdown", "metadata": {}, "source": t.strip().split("\n")}
def code(t): return {"cell_type": "code", "metadata": {}, "execution_count": None,
                     "outputs": [], "source": t.strip().split("\n")}

cells = [
md("""
# BrightBasket — Where Is Our Order Margin Leaking?

**Business question:** Orders grew 30% year on year but contribution margin stayed flat.
Which orders are we losing money on, and what is the single highest-value policy change
we can make without wrecking volume?

**Decision this analysis has to support:** the founder has to pick ONE of three levers —
restrict COD, raise the free-delivery threshold, or switch courier partner — and defend
it to the board. My job is to say which one, how much it is worth, and what it costs.

**How to read this notebook.** Every section ends with a `SO WHAT` cell. If a piece of
analysis cannot produce one, it does not belong in the notebook.
"""),

md("## 1. Load and audit\n\nAudit before cleaning. You cannot state the impact of a fix you never measured."),
code("""
import pandas as pd, numpy as np
pd.set_option('display.width', 180)

orders    = pd.read_csv('../data/raw/orders.csv')
customers = pd.read_csv('../data/raw/customers.csv')
pincodes  = pd.read_csv('../data/raw/pincodes.csv')
logistics = pd.read_csv('../data/raw/logistics.csv')

print(orders.shape, customers.shape, pincodes.shape, logistics.shape)
orders.head(3)
"""),
code("""
# Defect inventory. Each line becomes a row in the README's cleaning table.
print('rows                 ', len(orders))
print('duplicate order_ids  ', orders.order_id.duplicated().sum())
print('missing pincode      ', orders.pincode.isna().sum())
print('negative discounts   ', (orders.discount_amount < 0).sum())
print('zero-value orders    ', (orders.gross_order_value == 0).sum())
print('distinct cities      ', pincodes.city.nunique(), '<- suspicious, there are 15 real cities')
print(sorted(pincodes.city.unique())[:6])
"""),
md("""
**Why I check `order_id` first.** One row should mean one order. If an id repeats, every
total for revenue and cost comes out too high, and you can't tell by looking because the
margin percentage still looks normal. It usually happens when a data load job runs twice
and adds the rows again instead of replacing them.

**Why the city count matters.** There are 15 real cities. If the file shows more than 15
distinct values, the same city is written different ways. Grouping by city would split
Bengaluru into three rows. Always look at the distinct values before grouping on a column.
"""),

md("## 2. Cleaning — each step with its business justification"),
code("""
# 2a. Drop duplicate order_ids, keep first.
orders = orders.drop_duplicates(subset='order_id', keep='first')

# 2b. Mixed date formats (one upstream system writes DD-MM-YYYY).
#     format='mixed' parses each row on its own terms. The alternative,
#     errors='coerce', would silently turn 900 real dates into NaT.
orders['order_date'] = pd.to_datetime(orders.order_date, format='mixed', dayfirst=True)

# 2c. Negative discounts -> absolute. A discount is a magnitude; the minus sign
#     is a booking error from a refund posted to the wrong field. Flag, don't delete,
#     so the correction stays auditable.
orders['discount_flag_fixed'] = orders.discount_amount < 0
orders['discount_amount'] = orders.discount_amount.abs()

# 2d. Internal QA orders are not demand.
orders = orders[orders.customer_id != 'INTERNAL_QA']
"""),
code("""
# 2e. Missing pincodes -- BIAS CHECK BEFORE DROPPING.
# Dropping rows is only safe if what leaves resembles what stays. If missing
# pincodes were 90% COD, dropping them would delete the exact evidence I need.
lost = orders.pincode.isna()
print(f'dropping {lost.sum()} rows ({100*lost.mean():.2f}%)')
print('\\npayment mix of dropped rows:')
print(orders.loc[lost, 'payment_mode'].value_counts(normalize=True).round(3))
print('\\npayment mix of kept rows:')
print(orders.loc[~lost, 'payment_mode'].value_counts(normalize=True).round(3))
"""),
md("""
**So what:** the rows I'm dropping are 53% COD, and the rows I'm keeping are 57% COD. Close
enough that dropping them doesn't change the payment-mode answer, which is what the whole
project rests on. If it had been 90% COD I'd have had to work out the zone from the city
field instead, or flag it heavily.

This check takes thirty seconds and it's the difference between "I dropped 1.5% of rows"
and "I dropped 1.5% of rows and here's why that's safe."
"""),
code("""
orders = orders[~lost].copy()
orders['pincode'] = orders.pincode.astype(int)
pincodes['city'] = pincodes.city.str.strip().str.title()

# Join order. Orders is the fact table and stays on the left throughout, so no
# join can ever delete an order without me choosing to.
df = (orders
      .merge(pincodes,  on='pincode',     how='left')
      .merge(logistics, on='order_id',    how='left')
      .merge(customers, on='customer_id', how='left'))

# 2f. Cancelled orders were never dispatched, so a forward shipping charge on
#     them is a 3PL billing error. Worth flagging to ops as its own finding.
phantom = (df.order_status == 'Cancelled') & (df.forward_shipping_cost > 0)
print(f'phantom shipping charges: {phantom.sum()} rows, '
      f'Rs {df.loc[phantom,"forward_shipping_cost"].sum():,.0f} billed in error')
df.loc[phantom, 'forward_shipping_cost'] = 0.0

print(f'\\nrows retained: {len(df):,}')
"""),

md("""
## 3. Build the metric: contribution margin per order

**Why contribution margin and not gross margin or net profit.**

- *Gross margin* (revenue − COGS) sits **above** shipping and RTO in the P&L, so it hides
  the entire problem. Every order in this dataset looks fine on gross margin.
- *Net profit* needs fixed costs — salaries, warehouse rent, brand marketing — that do not
  change when one more order happens. Allocating them per order requires an arbitrary rule
  I could not defend, and it would make small orders look worse for reasons unrelated to
  the decision.
- *Contribution margin* = revenue minus every cost that **varies with this specific order**.
  That is exactly the right unit for a question shaped like "should we keep accepting orders
  like this one?" If contribution margin is negative, each additional order makes the
  company poorer, full stop.

**Why RTO is modelled at 15% COGS and not 100%.** On a return-to-origin the goods physically
come back to the warehouse and get resold. We do not lose the stock — we lose the damaged,
expired and unsellable share, plus we have paid shipping twice. Charging full COGS on an RTO
would roughly double the apparent loss and make the recommendation look better than it is.
"""),
code("""
COD_FEE, PG_RATE, RTO_WRITEOFF = 25.0, 0.02, 0.15

# net_order_value = what the order was WORTH   (exists for every order)
# net_revenue     = what we actually COLLECTED (zero unless delivered)
# Keeping these separate is not pedantry: banding orders by *revenue* would push
# every RTO into the 'Under 300' bucket and silently corrupt the value analysis.
df['net_order_value'] = df.gross_order_value - df.discount_amount
df['net_revenue']     = np.where(df.order_status == 'Delivered', df.net_order_value, 0.0)
df['delivery_revenue']= np.where(df.order_status == 'Delivered', df.delivery_fee_charged, 0.0)

df['cogs_effective'] = np.select(
    [df.order_status == 'Delivered', df.order_status == 'RTO'],
    [df.product_cost,                df.product_cost * RTO_WRITEOFF], default=0.0)

df['shipping_cost'] = df.forward_shipping_cost.fillna(0) + df.rto_shipping_cost.fillna(0)

# Payment cost is asymmetric, and that asymmetry is half the story:
#   prepaid -> 2% gateway fee, scales with order value
#   COD     -> flat Rs 25 cash-handling fee, and only if it actually delivers
df['payment_cost'] = np.where(
    (df.order_status == 'Delivered') & (df.payment_mode == 'COD'), COD_FEE,
    np.where((df.order_status == 'Delivered') & (df.payment_mode == 'Prepaid'),
             (df.net_revenue + df.delivery_revenue) * PG_RATE, 0.0)).round(2)

df['contribution_margin'] = (df.net_revenue + df.delivery_revenue
                             - df.cogs_effective - df.shipping_cost - df.payment_cost).round(2)
df['is_loss'] = df.contribution_margin < 0
df['value_band'] = pd.cut(df.net_order_value, [-1,299,499,699,999,1e9],
                          labels=['Under 300','300-499','500-699','700-999','1000+'])
df[['order_id','payment_mode','zone','order_status','net_order_value',
    'shipping_cost','contribution_margin']].head()
"""),

md("## Q1. How big is the leak?"),
code("""
rev = (df.net_revenue + df.delivery_revenue).sum()
cm  = df.contribution_margin.sum()
burn = df.loc[df.is_loss, 'contribution_margin'].sum()
earn = df.loc[~df.is_loss, 'contribution_margin'].sum()
print(f'revenue            Rs {rev:>12,.0f}')
print(f'contribution margin Rs {cm:>11,.0f}  ({100*cm/rev:.1f}%)')
print(f'loss-making orders  {df.is_loss.sum():,} ({100*df.is_loss.mean():.1f}%)')
print(f'margin burned      Rs {burn:>12,.0f}')
print(f'margin earned      Rs {earn:>12,.0f}')
print(f'\\nthe leak destroys {100*abs(burn)/earn:.1f}% of everything the good orders earn')
"""),
md("""
**So what:** 28% of orders lose ₹11.5 lakh, which is 26% of everything the profitable orders
make. Fixing it is worth more than growing sales 26%, and it costs nothing but a rule change.

**Why I split the profitable and loss-making orders instead of just reporting 15%.** A single
blended number lets the good orders cover for the bad ones, which is how a problem like this
survives for years. The blended figure looks fine. Splitting it shows what's actually fixable.
"""),

md("## Q2. Where is it concentrated?"),
code("""
seg = (df.groupby(['zone','payment_mode'], observed=True)
         .agg(orders=('order_id','count'),
              rto_rate=('order_status', lambda s: round(100*(s=='RTO').mean(),1)),
              avg_order_value=('net_order_value','mean'),
              cm_per_order=('contribution_margin','mean'),
              cm_total=('contribution_margin','sum'))
         .round(1).sort_values('cm_per_order'))
seg
"""),
md("""
**SO WHAT:** exactly one of six segments is negative — COD in Tier 3, at −₹4/order on a
16.3% RTO rate. Every other segment makes money.

**Why I cut by zone AND payment mode together rather than one at a time.** These two variables
are correlated in the real world: COD share is 46% in metros and 79% in tier 3. Looking at
either alone gives a confounded answer. The two-way cut is the cheapest possible control, and
it is the reason my conclusion differs from the obvious one.

**Why both `cm_per_order` and `cm_total` are in the table.** Per-order says how bad a segment
is; total says how much it matters. A segment can be dreadful per order and irrelevant in
total. Reporting only one is the classic fresher mistake — it leads to recommending a fix for
a problem worth ₹4,000.
"""),

md("## Q3. Is it COD itself, or something COD travels with?"),
code("""
print('NAIVE CUT (this is the trap):')
print(df.groupby('payment_mode').contribution_margin.agg(['count','mean']).round(1), '\\n')

print('WHY IT IS CONFOUNDED -- COD is not randomly assigned across zones:')
zone_mix = (df.assign(is_cod=(df.payment_mode == 'COD'))
              .groupby('zone')
              .agg(cod_share_pct=('is_cod', 'mean'),
                   avg_shipping=('shipping_cost', 'mean')))
zone_mix['cod_share_pct'] = (100 * zone_mix.cod_share_pct).round(1)
print(zone_mix.round(1), '\\n')

print('CONTROLLED CUT -- hold zone constant and ask again:')
print(df.pivot_table(index='zone', columns='payment_mode',
                     values='contribution_margin', aggfunc='mean').round(1))
"""),
md("""
**So what:** looking at payment mode alone, COD makes ₹60 an order and prepaid makes ₹114.
That looks like a clear case for restricting COD. It isn't. Once I compare within each zone,
**COD in metros makes ₹92 an order** — a good order, and one that brings in customers who
won't pay online.

The COD penalty is real but small in metros and catastrophic in tier 3, where it collides
with a 16% RTO rate and ₹139 all-in shipping. So the recommendation must be **geographic, not
payment-wide**. This one query is the difference between a ₹2L recovery and a ₹9L own goal.

**The general technique:** if a difference survives controlling for the confounder, it is
probably real. If it collapses, it was never there. The question to ask of any two groups
you are comparing is *"what else is unevenly distributed between them?"*
"""),

md("## Q4. Is our worst courier actually bad?"),
code("""
print('Raw ranking -- BharatShip looks terrible:')
print(df.groupby('courier_partner').contribution_margin.mean().round(1).sort_values(), '\\n')

print('Route mix -- the actual explanation:')
mix = df.pivot_table(index='courier_partner', columns='zone', values='order_id', aggfunc='count')
print((100*mix.div(mix.sum(axis=1), axis=0)).round(1), '\\n')

print('Compared only where they compete -- within the same zone:')
print(df.pivot_table(index='courier_partner', columns='zone',
                     values='contribution_margin', aggfunc='mean').round(1))
"""),
md("""
**So what: don't change courier.** BharatShip runs 38.5% of its deliveries in tier 3 and
SwiftLogix runs 3.5%. They're not worse, they just get the hard routes, usually because
they're the only ones who go there. Inside every zone all three are within a few rupees of
each other. Changing partners would have taken weeks and achieved nothing, because what drives
the cost is where we ship, not who ships it.

This is Simpson's paradox — a pattern that reverses when you split by a lurking variable.
Knowing the name is worth little. Knowing to always ask "what is unevenly distributed across
these groups?" is worth a lot.

Being able to say *"I checked this and recommended no action"* is a stronger interview moment
than any positive finding, because it shows you can kill your own idea.
"""),

md("## Q5. What is our own free-delivery policy costing us?"),
code("""
band = (df.groupby('value_band', observed=True)
          .agg(orders=('order_id','count'),
               avg_fee_charged=('delivery_revenue','mean'),
               avg_shipping_cost=('shipping_cost','mean'),
               cm_per_order=('contribution_margin','mean'),
               cm_total=('contribution_margin','sum')).round(1))
band['delivery_gap'] = (band.avg_fee_charged - band.avg_shipping_cost).round(1)
band
"""),
md("""
**Why these band edges.** The boundaries sit at 300 / 500 / 700 / 1000 so that one boundary
lands exactly on the ₹499 policy line. With even ₹250 buckets the cliff would be smeared
across two buckets and invisible. **Bucket edges belong on decision boundaries, not on round
numbers.** This is a question you will get asked.

**SO WHAT — three findings in one table:**
1. Orders under ₹300 lose ₹22 each. We charge ₹49 for delivery; it costs ₹87. The fee has
   never been repriced against actual cost.
2. The ₹500–699 band earns ₹53/order while ₹700–999 earns ₹182 — a **3.4× jump** across what
   is essentially a ₹1 difference in order value. That gap is not customer behaviour, it is
   our threshold. We hand ₹87 of free shipping to orders carrying ~₹140 of gross margin.
3. The threshold is simply set in the wrong place: ₹499 sits below the value at which an
   order can absorb its own delivery cost.
"""),

md("## Q6. What should we do, and what is it worth?"),
code("""
target = df[(df.payment_mode=='COD') & (df.zone=='Tier3') & (df.net_order_value<700)]
analogue = df[(df.payment_mode=='Prepaid') & (df.zone=='Tier3') & (df.net_order_value<700)]

CONVERT = 0.35   # stated assumption -- see docs/ASSUMPTIONS.md
avoided   = -target.contribution_margin.sum()
recovered = len(target) * CONVERT * analogue.contribution_margin.mean()

print(f'TARGET POCKET: COD + Tier3 + net value < Rs 700')
print(f'  {len(target):,} orders ({100*len(target)/len(df):.1f}% of volume), '
      f'RTO {100*(target.order_status=="RTO").mean():.1f}%')
print(f'  current margin  Rs {target.contribution_margin.sum():>10,.0f} '
      f'(Rs {target.contribution_margin.mean():.1f}/order)\\n')
print(f'LEVER 1 -- prepaid-only in that pocket, assuming {CONVERT:.0%} convert:')
print(f'  losses avoided       Rs {avoided:>10,.0f}   <- does NOT depend on the assumption')
print(f'  margin from converts Rs {recovered:>10,.0f}   <- does depend on it')
print(f'  NET GAIN             Rs {avoided+recovered:>10,.0f}')
print(f'  revenue given up     Rs {target.net_order_value.sum()*(1-CONVERT):>10,.0f}  '
      f'<- the honest cost\\n')

below = df[(df.net_order_value.between(500,698)) & (df.order_status=='Delivered')]
lever2 = len(below) * 49 * 0.75
print(f'LEVER 2 -- move free-delivery threshold Rs 499 -> Rs 699:')
print(f'  {len(below):,} orders newly pay Rs 49; at 75% retention -> Rs {lever2:,.0f}\\n')
print(f'COMBINED ANNUAL RECOVERY: Rs {avoided+recovered+lever2:,.0f} '
      f'({100*(avoided+recovered+lever2)/df.contribution_margin.sum():.1f}% lift on current CM)')
"""),
md("""
### Sensitivity — the part that makes this defensible

The 35% conversion rate is a **judgement, not a measurement**. So the honest question is:
at what value does the recommendation stop being right?

**It never does.** The ₹1.82L of losses avoided does not depend on anyone converting — it
happens the moment we stop accepting the loss-making order. Conversion only changes the size
of the upside, never its sign. Lever 1 is net-positive even at 0% conversion.

**The real cost, stated plainly:** roughly ₹9.6L of top-line revenue walks away. That revenue
carried negative margin, so losing it improves profit. But if the company is optimising for
GMV ahead of a fundraise, that trade-off is a business decision above the analyst's pay grade,
and my job is to surface it rather than pretend it does not exist.
"""),

md("## Export for the dashboard"),
code("""
keep = ['order_id','order_date','city','state','zone','category','payment_mode',
        'courier_partner','acquisition_channel','order_status','net_order_value',
        'net_revenue','delivery_revenue','cogs_effective','shipping_cost',
        'payment_cost','contribution_margin','is_loss','value_band']
df[keep].to_csv('../data/processed/order_economics.csv', index=False)
print(f'exported {len(df):,} rows')
"""),
md("""
**Why I export a row-level file rather than pre-aggregated summaries.** The dashboard needs to
support filtering by zone, payment mode and value band *simultaneously* — a pre-aggregated
table can only answer the cuts I anticipated. 39k rows is trivial for Tableau or Power BI, so
there is no performance reason to aggregate early, and aggregating early is how you end up
rebuilding the extract every time someone asks a follow-up question.
"""),
]

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3",
      "language": "python", "name": "python3"},
      "language_info": {"name": "python", "version": "3.11"}},
      "nbformat": 4, "nbformat_minor": 5}

for c in nb["cells"]:
    c["source"] = [l + "\n" for l in c["source"][:-1]] + [c["source"][-1]]

out = Path(__file__).resolve().parents[1] / "notebooks" / "01_cleaning_and_analysis.ipynb"
out.write_text(json.dumps(nb, indent=1))
print("wrote", out)
