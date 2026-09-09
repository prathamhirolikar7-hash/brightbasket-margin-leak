-- =============================================================================
-- 05_threshold_and_scenario.sql   -- Questions 5 and 6
-- =============================================================================

-- =============================================================================
-- Q5. WHAT IS OUR OWN FREE-DELIVERY POLICY COSTING US?
--
-- WHY I LOOKED HERE: Q2-Q4 explained tier 3, but tier 3 is only 15% of volume
-- and the loss-making orders were 28%. Something else is bleeding. The obvious
-- suspect is a policy WE set: free delivery above Rs 499 net.
--
-- WHY THESE BANDS: the boundaries are set at 300 / 500 / 700 / 1000 so that
-- one boundary sits exactly on the Rs 499 policy line. If I had used even
-- Rs 250 buckets the cliff would be smeared across two buckets and invisible.
-- Bucket edges should be placed on decision boundaries, not on round numbers.
-- =============================================================================
SELECT
    value_band,
    COUNT(*)                                     AS orders,
    ROUND(AVG(delivery_revenue), 1)              AS avg_fee_charged,
    ROUND(AVG(shipping_cost), 1)                 AS avg_shipping_cost,
    ROUND(AVG(delivery_revenue) - AVG(shipping_cost), 1) AS delivery_gap,
    ROUND(AVG(contribution_margin), 1)           AS cm_per_order,
    ROUND(SUM(contribution_margin), 0)           AS cm_total
FROM order_economics
GROUP BY value_band
ORDER BY MIN(net_order_value);

-- SO WHAT (three findings in one table):
-- 1. Orders under Rs 300 lose Rs 22 each. We charge Rs 49 for delivery and it
--    costs us Rs 87. The fee has not been repriced against actual cost.
-- 2. The Rs 500-699 band earns Rs 53/order while Rs 700-999 earns Rs 182 --
--    a 3.4x jump across an Rs 1 boundary in value. That gap is not customer
--    behaviour, it is our threshold. We hand Rs 87 of free shipping to orders
--    that only carry ~Rs 140 of gross margin.
-- 3. The threshold is set at the wrong place: Rs 499 is below the value at
--    which an order can actually absorb its own delivery cost.


-- =============================================================================
-- Q6. WHAT EXACTLY SHOULD WE DO, AND WHAT IS IT WORTH?
--
-- WHY I DEFINE THE TARGET WITH THREE CONDITIONS INSTEAD OF ONE:
-- each condition earned its place in Q2-Q5. COD alone is too broad (kills
-- profitable metro COD). Tier 3 alone is too broad (tier-3 prepaid is fine at
-- Rs 73/order). Low value alone is too broad. The intersection is the actual
-- loss pocket -- small, specific, and defensible.
-- =============================================================================
SELECT
    COUNT(*)                                       AS target_orders,
    ROUND(100.0 * COUNT(*)
        / (SELECT COUNT(*) FROM order_economics), 1) AS pct_of_all_orders,
    ROUND(100.0 * SUM(CASE WHEN order_status = 'RTO' THEN 1 ELSE 0 END)
              / COUNT(*), 1)                       AS rto_rate_pct,
    ROUND(AVG(contribution_margin), 1)             AS cm_per_order,
    ROUND(SUM(contribution_margin), 0)             AS cm_total,
    ROUND(SUM(net_order_value), 0)                 AS gross_order_value_at_risk
FROM order_economics
WHERE payment_mode = 'COD'
  AND zone = 'Tier3'
  AND net_order_value < 700;

-- The comparison group that makes the scenario credible.
-- WHY: to estimate what a converted order is worth I do not guess -- I use the
-- margin we ALREADY earn on prepaid orders of the same size in the same zone.
-- An estimate anchored on observed behaviour beats an assumed number.
SELECT
    COUNT(*)                           AS prepaid_analogue_orders,
    ROUND(AVG(contribution_margin), 1) AS cm_per_order
FROM order_economics
WHERE payment_mode = 'Prepaid'
  AND zone = 'Tier3'
  AND net_order_value < 700;

-- Lever 2 sizing: orders that would newly pay a delivery fee if the free
-- threshold moved from Rs 499 to Rs 699.
SELECT COUNT(*)          AS orders_newly_charged,
       ROUND(COUNT(*) * 49 * 0.75, 0) AS fee_revenue_at_75pct_retention
FROM order_economics
WHERE order_status = 'Delivered'
  AND net_order_value >= 500
  AND net_order_value < 699;

-- =============================================================================
-- THE SCENARIO, STATED HONESTLY
--
-- Assumption: 35% of blocked COD customers switch to prepaid, 65% do not buy.
-- I do NOT have data to prove 35%. It is a judgement anchored on published
-- Indian D2C prepaid-conversion ranges (25-45%) and deliberately set at the
-- pessimistic-middle. The right way to present an assumption you cannot verify
-- is to name it, show the range, and show the number at which the decision
-- would flip -- not to bury it.
--
-- BREAK-EVEN: this policy stays net-positive even at a 0% conversion rate,
-- because the losses avoided (Rs 1.82L) do not depend on anyone converting.
-- The conversion assumption only affects the size of the upside, never its
-- sign. That is what makes this a safe recommendation.
--
-- The honest cost: Rs 9.6L of top-line revenue walks away. That revenue was
-- carrying negative margin, so losing it improves profit -- but if the company
-- is optimising for GMV growth ahead of a fundraise, this trade-off is a
-- business decision above my pay grade and I should present it as such, not
-- pretend it does not exist.
-- =============================================================================
