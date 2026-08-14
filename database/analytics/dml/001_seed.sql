BEGIN;


INSERT INTO customers (
    name,
    segment,
    country,
    city,
    created_at
)
VALUES
    (
        'Acme Corp',
        'enterprise',
        'Mexico',
        'Mexico City',
        '2025-01-15'
    ),
    (
        'Globex',
        'enterprise',
        'Mexico',
        'Monterrey',
        '2025-02-01'
    ),
    (
        'Initech',
        'mid_market',
        'Mexico',
        'Guadalajara',
        '2025-02-20'
    ),
    (
        'Umbrella SA',
        'enterprise',
        'Colombia',
        'Bogota',
        '2025-03-10'
    ),
    (
        'Stark Industries',
        'enterprise',
        'United States',
        'New York',
        '2025-01-05'
    ),
    (
        'Wayne Enterprises',
        'enterprise',
        'United States',
        'Gotham',
        '2025-04-01'
    ),
    (
        'Soylent Corp',
        'mid_market',
        'Mexico',
        'Mexico City',
        '2025-05-01'
    ),
    (
        'Hooli',
        'mid_market',
        'United States',
        'San Francisco',
        '2025-05-20'
    );


INSERT INTO products (
    sku,
    name,
    category,
    price
)
VALUES
    (
        'ANALYTICS-PRO',
        'Analytics Pro',
        'analytics',
        1500.00
    ),
    (
        'DASHBOARD',
        'Executive Dashboard',
        'analytics',
        900.00
    ),
    (
        'DATA-CONNECT',
        'Data Connector',
        'integration',
        650.00
    ),
    (
        'AI-ASSIST',
        'AI Assistant',
        'ai',
        2200.00
    ),
    (
        'SUPPORT-PRO',
        'Premium Support',
        'services',
        500.00
    );


INSERT INTO orders (
    customer_id,
    status,
    total,
    created_at
)
VALUES
    (1, 'completed', 6000.00, '2026-05-10'),
    (1, 'completed', 4400.00, '2026-06-15'),
    (1, 'completed', 6600.00, '2026-07-20'),

    (2, 'completed', 3000.00, '2026-05-12'),
    (2, 'completed', 4500.00, '2026-06-18'),
    (2, 'completed', 5000.00, '2026-07-08'),

    (3, 'completed', 1800.00, '2026-05-03'),
    (3, 'completed', 2450.00, '2026-06-22'),
    (3, 'completed', 3100.00, '2026-07-25'),

    (4, 'completed', 8800.00, '2026-05-14'),
    (4, 'completed', 6600.00, '2026-06-10'),
    (4, 'completed', 9000.00, '2026-07-16'),

    (5, 'completed', 12000.00, '2026-05-01'),
    (5, 'completed', 13500.00, '2026-06-03'),
    (5, 'completed', 15000.00, '2026-07-04'),

    (6, 'completed', 5000.00, '2026-05-11'),
    (6, 'completed', 7000.00, '2026-06-17'),
    (6, 'completed', 8500.00, '2026-07-21'),

    (7, 'completed', 1300.00, '2026-06-12'),
    (7, 'completed', 1800.00, '2026-07-11'),

    (8, 'completed', 2800.00, '2026-06-30'),
    (8, 'completed', 3500.00, '2026-07-30'),

    (3, 'cancelled', 5000.00, '2026-07-28'),
    (7, 'refunded', 2200.00, '2026-07-29');


INSERT INTO order_items (
    order_id,
    product_id,
    quantity,
    unit_price
)
VALUES
    -- order 1: 6000
    (1, 1, 1, 1500.00),
    (1, 2, 5, 900.00),
    -- order 2: 4400
    (2, 4, 2, 2200.00),
    -- order 3: 6600
    (3, 4, 3, 2200.00),
    -- order 4: 3000
    (4, 1, 2, 1500.00),
    -- order 5: 4500
    (5, 1, 3, 1500.00),
    -- order 6: 5000
    (6, 4, 1, 2200.00),
    (6, 1, 1, 1500.00),
    (6, 3, 2, 650.00),
    -- order 7: 1800
    (7, 2, 2, 900.00),
    -- order 8: 2450
    (8, 5, 1, 500.00),
    (8, 3, 3, 650.00),
    -- order 9: 3100
    (9, 2, 1, 900.00),
    (9, 4, 1, 2200.00),
    -- order 10: 8800
    (10, 4, 4, 2200.00),
    -- order 11: 6600
    (11, 4, 3, 2200.00),
    -- order 12: 9000
    (12, 1, 6, 1500.00),
    -- order 13: 12000
    (13, 1, 8, 1500.00),
    -- order 14: 13500
    (14, 1, 9, 1500.00),
    -- order 15: 15000
    (15, 4, 5, 2200.00),
    (15, 5, 8, 500.00),
    -- order 16: 5000
    (16, 4, 1, 2200.00),
    (16, 1, 1, 1500.00),
    (16, 3, 2, 650.00),
    -- order 17: 7000
    (17, 1, 2, 1500.00),
    (17, 4, 1, 2200.00),
    (17, 2, 2, 900.00),
    -- order 18: 8500
    (18, 4, 3, 2200.00),
    (18, 2, 1, 900.00),
    (18, 5, 2, 500.00),
    -- order 19: 1300
    (19, 3, 2, 650.00),
    -- order 20: 1800
    (20, 2, 2, 900.00),
    -- order 21: 2800
    (21, 3, 2, 650.00),
    (21, 5, 3, 500.00),
    -- order 22: 3500
    (22, 1, 2, 1500.00),
    (22, 5, 1, 500.00),
    -- order 23: 5000 (cancelled)
    (23, 4, 1, 2200.00),
    (23, 1, 1, 1500.00),
    (23, 3, 2, 650.00),
    -- order 24: 2200 (refunded)
    (24, 4, 1, 2200.00);


COMMIT;