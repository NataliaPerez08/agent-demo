CREATE VIEW completed_orders AS
SELECT
    o.id,
    o.customer_id,
    o.total,
    o.created_at
FROM orders o
WHERE o.status = 'completed';


CREATE VIEW customer_revenue AS
SELECT
    c.id AS customer_id,
    c.name AS customer_name,
    c.segment,
    c.country,
    c.city,

    COUNT(o.id) AS total_orders,

    COALESCE(
        SUM(o.total),
        0
    ) AS total_revenue,

    MAX(o.created_at) AS last_order_at

FROM customers c

LEFT JOIN completed_orders o
    ON o.customer_id = c.id

GROUP BY
    c.id,
    c.name,
    c.segment,
    c.country,
    c.city;


CREATE VIEW product_sales AS
SELECT
    p.id AS product_id,
    p.sku,
    p.name AS product_name,
    p.category,

    COALESCE(
        SUM(s.quantity),
        0
    ) AS units_sold,

    COALESCE(
        SUM(
            s.quantity * s.unit_price
        ),
        0
    ) AS revenue

FROM products p

LEFT JOIN (
    SELECT
        oi.product_id,
        oi.quantity,
        oi.unit_price
    FROM order_items oi
    JOIN completed_orders co
        ON co.id = oi.order_id
) s
    ON s.product_id = p.id

GROUP BY
    p.id,
    p.sku,
    p.name,
    p.category;