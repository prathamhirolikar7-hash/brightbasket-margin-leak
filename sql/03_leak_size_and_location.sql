-- =============================================================================
-- 03_leak_size_and_location.sql   -- Questions 1 and 2
-- =============================================================================

-- =============================================================================
-- Q1. HOW BIG IS THE LEAK, AND IS IT WORTH A MEETING?
--
-- WHY THIS QUERY FIRST: before diagnosing anything I have to prove the problem
-- is material. If loss-making orders were 0.3% of volume, the honest answer is
-- "there is no project here" and I should say so. Sizing first also gives me
-- the denominator for every later claim.
--
-- WHY I SPLIT PROFITABLE FROM LOSS-MAKING RATHER THAN JUST REPORTING THE TOTAL:
-- a single blended margin of 15% looks fine and hides everything. Netting a
-- loss-making segment against a profitable one is how a leak survives for
-- years. Splitting them shows the gross size of what is fixable.
-- =============================================================================
SELECT
    COUNT(*)                                                   AS total_orders,
    ROUND(SUM(net_revenue + delivery_revenue), 0)              AS total_revenue,
    ROUND(SUM(contribution_margin), 0)                         AS total_cm,
    ROUND(100.0 * SUM(contribution_margin)
              / SUM(net_revenue + delivery_revenue), 1)        AS cm_pct,
    SUM(CASE WHEN contribution_margin < 0 THEN 1 ELSE 0 END)   AS loss_orders,
    ROUND(100.0 * SUM(CASE WHEN contribution_margin < 0 THEN 1 ELSE 0 END)
              / COUNT(*), 1)                                   AS loss_order_pct,
    ROUND(SUM(CASE WHEN contribution_margin < 0
                   THEN contribution_margin ELSE 0 END), 0)    AS margin_burned,
    ROUND(SUM(CASE WHEN contribution_margin >= 0
                   THEN contribution_margin ELSE 0 END), 0)    AS margin_earned
FROM order_economics;

-- SO WHAT: 28.4% of orders destroy Rs 11.5L, which is 26% of everything the
-- profitable orders earn. Fixing this is worth more than a 26% sales increase,
-- and costs nothing but a policy change. That justifies the rest of the work.


-- =============================================================================
-- Q2. WHERE IS THE LEAK CONCENTRATED?
--
-- WHY I CUT BY ZONE *AND* PAYMENT MODE TOGETHER RATHER THAN ONE AT A TIME:
-- these two variables are correlated in the real world -- COD share is far
-- higher outside metros. Looking at either alone gives a confounded answer.
-- The two-way cut is the cheapest possible control and it is the reason my
-- conclusion is different from the obvious one.
--
-- WHY cm_per_order AND cm_total SIDE BY SIDE: per-order tells me how bad a
-- segment is, total tells me how much it matters. A segment can be terrible
-- per order and irrelevant in total (150 orders). I need both to prioritise,
-- and reporting only one is the classic fresher mistake.
-- =============================================================================
SELECT
    zone,
    payment_mode,
    COUNT(*)                                                 AS orders,
    ROUND(100.0 * SUM(CASE WHEN order_status = 'RTO' THEN 1 ELSE 0 END)
              / COUNT(*), 1)                                 AS rto_rate_pct,
    ROUND(AVG(net_order_value), 0)                           AS avg_order_value,
    ROUND(AVG(contribution_margin), 1)                       AS cm_per_order,
    ROUND(SUM(contribution_margin), 0)                       AS cm_total
FROM order_economics
GROUP BY zone, payment_mode
ORDER BY cm_per_order ASC;

-- SO WHAT: exactly ONE of the six segments is negative -- COD in Tier 3, at
-- -Rs 4/order on a 16.3% RTO rate. Everything else makes money. That means the
-- fix is a targeted policy on ~12% of orders, not a company-wide change.
-- A blanket "stop offering COD" would have destroyed Rs 9L of profitable
-- metro COD margin to solve a Rs 18k problem.


-- =============================================================================
-- Q2b. Does category make it worse? (secondary cut, one level deeper)
-- WHY: gross margin % differs 3x across categories. A category at 18% margin
-- physically cannot absorb an Rs 118 tier-3 shipping cost; one at 55% can.
-- If the loss is category-driven too, the recommendation changes shape.
-- =============================================================================
SELECT
    category,
    COUNT(*)                             AS orders,
    ROUND(AVG(net_order_value), 0)       AS avg_order_value,
    ROUND(AVG(cogs_effective), 0)        AS avg_cogs,
    ROUND(AVG(shipping_cost), 0)         AS avg_shipping,
    ROUND(AVG(contribution_margin), 1)   AS cm_per_order
FROM order_economics
WHERE order_status = 'Delivered'
GROUP BY category
ORDER BY cm_per_order ASC;

-- SO WHAT: low-margin categories are thin but not the driver -- shipping cost
-- is roughly flat across categories while margin varies. The leak is a
-- delivery-economics problem, not a merchandising one. Naming what is NOT the
-- cause is as valuable as naming what is; it stops the business chasing the
-- wrong fix.
