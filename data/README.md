# What's in the data

## Where it came from

This data is made up. `scripts/generate_raw_data.py` creates it, using a fixed random seed
(`20260906`) so it comes out identical every time.

**Why made up.** The analysis needs product cost, shipping cost and return status for each
individual order, all together. That combination is a company's unit economics and nobody
publishes it. So I had a choice: pick a weaker question that public data could answer, or build
realistic data for the question that actually matters. I picked the second and left the generator
open so anyone can see exactly what I assumed. All the numbers behind it are in
`docs/ASSUMPTIONS.md`.

40,000 orders, 15 Indian cities, 121 pincodes, April 2025 to March 2026.

---

## `raw/orders.csv` — 40,180 rows

This is the messy version, before cleaning.

| Column | What it is |
|---|---|
| `order_id` | Should be unique. **180 rows are duplicated on purpose.** |
| `customer_id` | Links to customers.csv. `INTERNAL_QA` means a test order. |
| `order_date` | **Two different formats mixed together** — mostly YYYY-MM-DD, about 900 rows DD-MM-YYYY. |
| `pincode` | Links to pincodes.csv. **About 1.5% are blank.** |
| `category` | Skincare, Haircare, Baby Care, Home Cleaning, Household Staples |
| `payment_mode` | COD or Prepaid |
| `gross_order_value` | Order value before discount. 45 rows are ₹0 (test orders). |
| `discount_amount` | **120 rows are negative** — someone entered a refund in the wrong column. |
| `delivery_fee_charged` | ₹49 if the order is under ₹499, otherwise ₹0 |
| `product_cost` | What the goods cost us |
| `order_status` | Delivered, RTO (came back), or Cancelled |

## `raw/logistics.csv` — 40,000 rows

The courier's bill. Kept separate because that's how it actually arrives.

| Column | What it is |
|---|---|
| `order_id` | Links to orders.csv |
| `courier_partner` | SwiftLogix, BharatShip, ZipEx |
| `forward_shipping_cost` | What it cost us to send. **140 cancelled orders wrongly have a charge.** |
| `rto_shipping_cost` | The return trip, about 1.55× the outbound. Zero unless the order came back. |
| `delivery_attempts` | 1 to 3 |

## `raw/pincodes.csv` — 121 rows

| Column | What it is |
|---|---|
| `pincode` | The key |
| `city` | **Written inconsistently on purpose** — Bengaluru, BENGALURU, bengaluru |
| `state` | |
| `zone` | Metro, Tier2 or Tier3. This is the main thing I split the analysis by. |

## `raw/customers.csv` — 16,000 rows

| Column | What it is |
|---|---|
| `customer_id` | The key |
| `signup_date` | |
| `acquisition_channel` | Meta Ads, Google Ads, Organic, Influencer, Referral |

---

## `processed/order_economics.csv` — 39,355 rows

Cleaned, joined together, with the profit worked out. This is what the dashboard reads.

| Column | What it is |
|---|---|
| `net_order_value` | Order value after discount. **What the order was worth**, for every order regardless of what happened to it. |
| `net_revenue` | **What we actually collected.** Zero unless the order was delivered. |
| `delivery_revenue` | Delivery fee collected. Zero unless delivered. |
| `cogs_effective` | Full product cost if delivered, 15% written off if it came back, zero if cancelled. |
| `shipping_cost` | Outbound, plus the return trip if it came back. |
| `payment_cost` | 2% gateway fee on prepaid, ₹25 flat on COD. |
| `contribution_margin` | Revenue minus all of the above. The number the whole project is about. |
| `is_loss` | True if contribution_margin is below zero |
| `value_band` | Under 300, 300-499, 500-699, 700-999, 1000+ — based on **order value, not revenue** |

Two things worth explaining there.

**Why `net_order_value` and `net_revenue` are separate columns.** If I grouped orders by revenue,
every returned order would land in the "Under 300" bucket, because a returned order collects
nothing. That bug was actually in an early version. I only found it because the SQL and the pandas
versions started disagreeing.

**Why the band is called `Under 300` and not `<300`.** Excel and Power BI both read a leading `<`
in a filter as "less than", so `COUNTIFS(range,"<300")` matches nothing and returns zero with no
error at all. Don't put comparison symbols in labels you'll filter on later.
