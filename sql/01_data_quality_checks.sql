-- =============================================================================
-- 01_data_quality_checks.sql
-- Run this before any analysis.
--
-- The idea: count every problem before fixing it. That way I can say how many
-- rows I changed and why, instead of just saying the data was messy.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- CHECK 1: Is order_id actually unique?
-- One row should mean one order. If an id repeats, every total for revenue
-- and cost is too high, and nothing warns you. Usually happens when a data
-- load job runs twice and adds the rows again instead of replacing them.
-- -----------------------------------------------------------------------------
SELECT COUNT(*) AS total_rows,
       COUNT(DISTINCT order_id) AS unique_orders,
       COUNT(*) - COUNT(DISTINCT order_id) AS duplicate_rows
FROM orders;

-- Show me the duplicates so I can confirm they are true copies, not two
-- genuinely different orders that were assigned the same id (very different fix).
SELECT order_id, COUNT(*) AS n
FROM orders
GROUP BY order_id
HAVING COUNT(*) > 1
LIMIT 10;

-- -----------------------------------------------------------------------------
-- CHECK 2: Missing pincodes
-- WHY: zone is my primary analysis dimension. An order with no pincode cannot
-- be assigned to a zone, which means it cannot be assigned to a recommendation.
-- -----------------------------------------------------------------------------
SELECT COUNT(*) AS missing_pincode,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM orders), 2) AS pct
FROM orders
WHERE pincode IS NULL OR TRIM(pincode) = '';

-- Check before dropping.
-- Removing rows is only safe if the removed ones look like the kept ones.
-- If the missing pincodes were 90% COD, I'd be deleting exactly the orders
-- I'm investigating. So compare the payment split of both groups first.
SELECT CASE WHEN pincode IS NULL THEN 'dropped' ELSE 'kept' END AS bucket,
       payment_mode,
       COUNT(*) AS n
FROM orders
GROUP BY 1, 2;

-- -----------------------------------------------------------------------------
-- CHECK 3: Impossible values
-- WHY: a negative discount is not a discount, it is a booking error (a refund
-- posted to the wrong field). A zero-value order is not demand, it is a test.
-- Both distort averages if left in.
-- -----------------------------------------------------------------------------
SELECT SUM(CASE WHEN discount_amount < 0 THEN 1 ELSE 0 END)            AS negative_discounts,
       SUM(CASE WHEN gross_order_value = 0 THEN 1 ELSE 0 END)          AS zero_value_orders,
       SUM(CASE WHEN discount_amount > gross_order_value THEN 1 ELSE 0 END) AS discount_exceeds_value,
       SUM(CASE WHEN product_cost > gross_order_value THEN 1 ELSE 0 END)    AS cost_exceeds_price
FROM orders;

SELECT customer_id, COUNT(*) AS n
FROM orders
WHERE gross_order_value = 0
GROUP BY customer_id;   -- expect: INTERNAL_QA. Confirms these are test orders.

-- -----------------------------------------------------------------------------
-- CHECK 4: Referential integrity across the four tables
-- WHY: I am about to JOIN. If orders reference pincodes that do not exist in
-- the master, a LEFT JOIN gives me NULL zones and an INNER JOIN silently
-- deletes rows. I need to know which before I choose the join type.
-- -----------------------------------------------------------------------------
SELECT COUNT(*) AS orders_with_no_pincode_master
FROM orders o
LEFT JOIN pincodes p ON o.pincode = p.pincode
WHERE o.pincode IS NOT NULL AND p.pincode IS NULL;

SELECT COUNT(*) AS orders_with_no_logistics_row
FROM orders o
LEFT JOIN logistics l ON o.order_id = l.order_id
WHERE l.order_id IS NULL;

-- -----------------------------------------------------------------------------
-- CHECK 5: Logic contradictions between tables
-- WHY: a cancelled order was never dispatched, so it cannot have a forward
-- shipping cost. Finding 134 of these means the 3PL billed us in error --
-- that is itself a finding worth telling the ops team about, separate from
-- the main analysis.
-- -----------------------------------------------------------------------------
SELECT o.order_status,
       COUNT(*) AS n,
       SUM(l.forward_shipping_cost) AS total_forward_cost
FROM orders o
JOIN logistics l ON o.order_id = l.order_id
WHERE o.order_status = 'Cancelled' AND l.forward_shipping_cost > 0
GROUP BY o.order_status;

-- -----------------------------------------------------------------------------
-- CHECK 6: Dimension hygiene before any GROUP BY
-- WHY: 'Bengaluru', 'BENGALURU' and 'bengaluru' are three rows in a GROUP BY
-- and one city in reality. This splits a chart into meaningless slices. Always
-- inspect distinct values of a grouping column before grouping on it.
-- -----------------------------------------------------------------------------
SELECT city, COUNT(*) AS n_pincodes
FROM pincodes
GROUP BY city
ORDER BY city;
