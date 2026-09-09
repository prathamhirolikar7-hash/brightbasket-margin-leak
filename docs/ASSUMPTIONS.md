# Assumptions

Every number in this project that I assumed rather than measured, why I picked it, and how much
the answer would change if I got it wrong.

If someone asks "where did that number come from?", it's in here.

---

## Numbers used to build the dataset

These shape the made-up data. They come from published Indian e-commerce benchmarks. The point is
that they're written down and open, not that they're exactly right.

| What | Value | Why |
|---|---|---|
| Gross margin by category | Skincare 55%, Haircare 48%, Baby Care 38%, Home Cleaning 28%, Staples 18% | Beauty products in D2C usually run 45–60%. Commodity staples run under 25%. The 3× gap matters: a low-margin product can't absorb a ₹118 shipping cost. |
| Shipping cost one way | Metro ₹64, Tier 2 ₹88, Tier 3 ₹118 on average | Normal courier rates for a half-kilo parcel go up with distance. |
| Return leg cost | 1.55× the outbound cost | Return freight plus two extra handling steps. Usually quoted between 1.5 and 1.8. |
| Base return rate | Prepaid 1.8%, COD 7.0% | The gap between prepaid and COD returns is the most consistently reported figure in Indian e-commerce. |
| Extra returns for tier-3 COD | +8.5 points | Worse addresses, longer delivery times, more refusals at the door. |
| Extra returns on big discounts | +3 points above 25% off | Discount-driven impulse buys get refused more often. |
| COD share by zone | Metro 46%, Tier 2 66%, Tier 3 79% | Online payment adoption follows UPI use and delivery trust, both lower outside metros. This is the thing the whole analysis turns on. |
| Courier route split | BharatShip 38.5% tier 3, SwiftLogix 3.5% | Deliberate. Couriers with better reach get the harder routes. This is what creates the courier trap. |

---

## Assumptions that change the answer

### 15% write-off on returned goods

**What it means:** when an order comes back, I count 15% of the product cost as lost, not 100%.

**Why:** the goods physically come back to the warehouse and get sold again. What we actually lose
is the damaged and expired share, plus we've paid shipping twice.

**If I'm wrong:** at 30% write-off, tier-3 COD goes from −₹4 to about −₹19 per order, so the
recommendation gets stronger. At 5% it goes to about +₹3, which would weaken it a lot.

So this one matters, and 15% is deliberately the cautious end. Picking the assumption that makes
your own recommendation harder to defend is how you avoid kidding yourself.

### 35% of blocked COD customers switch to prepaid

**What it means:** if we stop offering COD to someone in the target group, 35% pay online instead
and 65% don't buy.

**Why 35%:** published Indian D2C figures for this sit between 25% and 45%. I took the middle,
leaning pessimistic.

**If I'm wrong — and this is the important bit:** it doesn't change the recommendation. The
₹1,81,825 of avoided losses happens the moment we stop taking the loss-making order, whether or not
anyone switches. Switching only affects how big the gain is, never whether there is one. The
recommendation makes money even at 0%.

**How to actually find out:** run a two-week test on five tier-3 pincodes. That's what I'd propose
before rolling it out, and it's a better answer than any guess.

### 75% of customers still buy after the delivery fee change

**What it means:** if we start charging ₹49 on orders between ₹500 and ₹699, I assume 75% of those
customers still order.

**Why:** ₹49 on a ₹600 order is about an 8% price rise. Normal price sensitivity in that range
suggests a single-digit to low-teens drop. 25% is deliberately pessimistic.

**If I'm wrong:** at 50% retention this falls from ₹3,73,968 to ₹2,49,312. Still the bigger of the
two recommendations, but a lot less.

**This is my weakest assumption and I'd say so first.** Unlike the other one, there's no
avoided-losses floor protecting it. It also ignores the possibility that some customers add another
item to get over ₹699 instead of dropping out, which would push the real number higher. I don't
know which effect wins.

### Payment costs: 2% gateway, ₹25 flat for COD

Indian payment gateways charge roughly 1.8–2.2% for cards and UPI. COD handling is billed by the
courier as a flat fee per order.

The difference matters. The gateway fee grows with order size; the COD fee doesn't. So COD is
relatively cheaper on big orders and more expensive on small ones, which lines up with the
value-band finding.

### I treated the cost of making these changes as zero

Both changes are settings in a checkout system. In reality there's developer time and probably a
spike in customer complaints. I haven't included either. On a ₹5.7 lakh gain it probably doesn't
change the decision, but I shouldn't pretend it's free. The first thing I'd ask an engineer is how
long the pincode blocking takes to build.

---

## Things I deliberately did not assume

**Customer lifetime value.** I could have assumed a repeat rate and argued the blocked customers
were worth more over time. I didn't, because I had nothing to base the number on. It's a genuine
gap in an order-level analysis and I'd rather say so than cover it with a made-up figure.

**Splitting fixed costs across orders.** Salaries, rent and brand marketing don't change when one
more order happens. Splitting them per order would need an arbitrary rule and would make small
orders look bad for reasons that have nothing to do with the decision.

**Seasonality.** One year of data isn't enough to tell a trend from noise.
