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


COMMIT;