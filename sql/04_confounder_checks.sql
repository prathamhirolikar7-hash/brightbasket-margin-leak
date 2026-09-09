-- =============================================================================
-- 04_confounder_checks.sql   -- Questions 3 and 4
--
-- These two queries are the heart of the project. Both take an answer that
-- looks obvious and show it's wrong.
-- =============================================================================

-- =============================================================================
-- Q3. IS COD ITSELF THE PROBLEM, OR SOMETHING COD TRAVELS WITH?
--
-- THE TRAP: the naive cut below says COD earns Rs 60/order and prepaid earns
-- Rs 114. Read alone it says "COD is destroying us, restrict it."
-- That conclusion is wrong, and acting on it would cost the business money.
-- =============================================================================

-- Step 1 -- the naive, confounded cut (shown deliberately, then refuted)
SELECT payment_mode,
       COUNT(*)                           AS orders,
       ROUND(AVG(contribution_margin), 1) AS cm_per_order
FROM order_economics
GROUP BY payment_mode;

-- Step 2 -- why it is confounded: COD is not randomly distributed across zones.
-- COD share is 46% in metros and 79% in tier 3. So "COD orders" is partly just
-- a relabelling of "tier-3 orders", which are expensive for reasons that have
-- nothing to do with the payment method.
SELECT zone,
       ROUND(100.0 * SUM(CASE WHEN payment_mode = 'COD' THEN 1 ELSE 0 END)
                 / COUNT(*), 1) AS cod_share_pct,
       ROUND(AVG(shipping_cost), 0) AS avg_shipping_cost
FROM order_economics
GROUP BY zone;

-- Step 3 -- hold zone constant and ask the question again.
-- This is the whole technique: if a difference survives controlling for the
-- confounder, it is probably real; if it collapses, it was never there.
SELECT zone,
       ROUND(AVG(CASE WHEN payment_mode = 'COD'     THEN contribution_margin END), 1) AS cod_cm,
       ROUND(AVG(CASE WHEN payment_mode = 'Prepaid' THEN contribution_margin END), 1) AS prepaid_cm,
       ROUND(AVG(CASE WHEN payment_mode = 'COD'     THEN contribution_margin END)
           - AVG(CASE WHEN payment_mode = 'Prepaid' THEN contribution_margin END), 1) AS gap
FROM order_economics
GROUP BY zone;

-- SO WHAT: COD in a metro earns Rs 92/order -- it is a profitable, useful
-- product that drives conversion. The COD penalty is real but it is small in
-- metros and catastrophic in tier 3, where it collides with a 16% RTO rate and
-- an Rs 139 average all-in shipping cost. The recommendation must therefore be geographic,
-- not payment-wide. This single query is the difference between a Rs 2L
-- recovery and a Rs 9L own goal.


-- =============================================================================
-- Q4. IS OUR WORST COURIER ACTUALLY BAD?
--
-- THE TRAP: BharatShip shows Rs 56/order vs SwiftLogix Rs 96. The obvious
-- action is "renegotiate or drop BharatShip." Also wrong, for the same reason.
-- =============================================================================

-- Step 1 -- the raw ranking that creates the false impression
SELECT courier_partner,
       COUNT(*)                           AS orders,
       ROUND(AVG(contribution_margin), 1) AS cm_per_order
FROM order_economics
GROUP BY courier_partner
ORDER BY cm_per_order ASC;

-- Step 2 -- the route mix, which is the actual explanation.
-- BharatShip carries 38.5% of its volume in tier 3; SwiftLogix carries 3.5%.
-- They are not worse, they are given the hard routes -- often because they are
-- the only partner with that reach.
SELECT courier_partner,
       ROUND(100.0 * SUM(CASE WHEN zone = 'Metro' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_metro,
       ROUND(100.0 * SUM(CASE WHEN zone = 'Tier2' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_tier2,
       ROUND(100.0 * SUM(CASE WHEN zone = 'Tier3' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_tier3
FROM order_economics
GROUP BY courier_partner;

-- Step 3 -- compare them only where they compete: within the same zone.
SELECT zone,
       courier_partner,
       COUNT(*)                           AS orders,
       ROUND(100.0 * SUM(CASE WHEN order_status = 'RTO' THEN 1 ELSE 0 END)
                 / COUNT(*), 1)           AS rto_rate_pct,
       ROUND(AVG(shipping_cost), 0)       AS avg_shipping_cost,
       ROUND(AVG(contribution_margin), 1) AS cm_per_order
FROM order_economics
GROUP BY zone, courier_partner
ORDER BY zone, cm_per_order DESC;

-- So what: inside every zone the three couriers are within a few rupees of
-- each other. There is no courier problem. Changing partners would have taken
-- weeks and achieved nothing, because what drives the cost is where we ship,
-- not who ships it. Recommendation: don't change courier.
--
-- This is called Simpson's paradox -- a pattern that flips once you split by
-- something hidden. The name matters less than the habit: always ask what else
-- is different between the two groups you're comparing.
