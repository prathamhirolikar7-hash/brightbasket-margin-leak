-- =============================================================================
-- 02_order_economics_view.sql
-- The most important file here. Everything else reads from this view.
--
-- Why a view instead of pasting the formula into every query:
-- if I later change the COD fee from Rs 25 to Rs 30, I change it once here.
-- Paste it into six queries and five of them go stale without warning.
--
-- Why contribution margin and not gross margin or net profit:
--   Gross margin is revenue minus product cost. Shipping and returns sit
--     below that line, so it hides the whole problem.
--   Net profit needs fixed costs like rent and salaries, which don't change
--     when one more order comes in. Splitting them per order needs a made-up
--     rule I couldn't defend.
--   Contribution margin is revenue minus every cost that only happens because
--     this order happened. That's the right thing to look at when the question
--     is "should we keep taking orders like this one?"
-- =============================================================================

DROP VIEW IF EXISTS order_economics;

CREATE VIEW order_economics AS
SELECT
    o.order_id,
    o.order_date,
    o.customer_id,
    p.city,
    p.state,
    p.zone,
    o.category,
    o.payment_mode,
    l.courier_partner,
    o.order_status,

    -- WHAT THE ORDER WAS WORTH (exists regardless of outcome)
    o.gross_order_value - o.discount_amount AS net_order_value,

    -- WHAT WE ACTUALLY COLLECTED
    -- An RTO order collects nothing. Booking its value as revenue and its
    -- shipping as cost would show a healthy top line hiding a total loss.
    CASE WHEN o.order_status = 'Delivered'
         THEN o.gross_order_value - o.discount_amount ELSE 0 END AS net_revenue,
    CASE WHEN o.order_status = 'Delivered'
         THEN o.delivery_fee_charged ELSE 0 END AS delivery_revenue,

    -- COST OF GOODS, ADJUSTED FOR OUTCOME
    -- Delivered: full COGS, the goods are gone.
    -- RTO: the goods come BACK, so we only lose the damaged/expired share.
    --      15% write-off is a stated assumption (see docs/ASSUMPTIONS.md).
    --      Charging full COGS on an RTO would double-count the loss.
    -- Cancelled: nothing shipped, nothing lost.
    CASE WHEN o.order_status = 'Delivered' THEN o.product_cost
         WHEN o.order_status = 'RTO'       THEN ROUND(o.product_cost * 0.15, 2)
         ELSE 0 END AS cogs_effective,

    -- SHIPPING: forward always, return leg only on RTO.
    -- This is why an RTO is roughly 2.5x worse than simply not getting the
    -- order -- we pay to send it and pay again to get it back.
    COALESCE(l.forward_shipping_cost, 0) + COALESCE(l.rto_shipping_cost, 0) AS shipping_cost,

    -- PAYMENT COST: not symmetric between the two modes, which is half the story.
    --   Prepaid -> 2% payment gateway fee on the collected amount.
    --   COD     -> flat Rs 25 cash-handling fee charged by the courier,
    --              and only on successful delivery (no collection on RTO).
    CASE
        WHEN o.order_status <> 'Delivered' THEN 0
        WHEN o.payment_mode = 'COD' THEN 25.0
        ELSE ROUND((o.gross_order_value - o.discount_amount + o.delivery_fee_charged) * 0.02, 2)
    END AS payment_cost,

    -- THE HEADLINE NUMBER
    ROUND(
        (CASE WHEN o.order_status = 'Delivered'
              THEN o.gross_order_value - o.discount_amount + o.delivery_fee_charged ELSE 0 END)
      - (CASE WHEN o.order_status = 'Delivered' THEN o.product_cost
              WHEN o.order_status = 'RTO'       THEN o.product_cost * 0.15 ELSE 0 END)
      - (COALESCE(l.forward_shipping_cost, 0) + COALESCE(l.rto_shipping_cost, 0))
      - (CASE WHEN o.order_status <> 'Delivered' THEN 0
              WHEN o.payment_mode = 'COD' THEN 25.0
              ELSE (o.gross_order_value - o.discount_amount + o.delivery_fee_charged) * 0.02 END)
    , 2) AS contribution_margin,

    -- Banding on ORDER VALUE, not revenue. Banding on revenue would push every
    -- RTO into the "Under 300" bucket (revenue = 0) and destroy the analysis.
    CASE
        -- Label is 'Under 300', not '<300': Excel and Power BI both read a
        -- leading '<' in a criteria string as the less-than OPERATOR, so
        -- COUNTIFS(band_range,"<300") silently matches zero rows. Avoid
        -- comparison characters in any label you will later filter on.
        WHEN o.gross_order_value - o.discount_amount < 300  THEN 'Under 300'
        WHEN o.gross_order_value - o.discount_amount < 500  THEN '300-499'
        WHEN o.gross_order_value - o.discount_amount < 700  THEN '500-699'
        WHEN o.gross_order_value - o.discount_amount < 1000 THEN '700-999'
        ELSE '1000+'
    END AS value_band

FROM orders o
-- LEFT JOIN, not INNER: I want to SEE orders whose pincode is missing rather
-- than have them vanish. A join that silently deletes rows is how analysts
-- lose 2% of revenue without noticing. I filter them out explicitly instead.
LEFT JOIN pincodes  p ON o.pincode  = p.pincode
LEFT JOIN logistics l ON o.order_id = l.order_id
WHERE o.customer_id <> 'INTERNAL_QA'   -- test orders, not demand
  AND o.pincode IS NOT NULL;           -- explicit, auditable exclusion
