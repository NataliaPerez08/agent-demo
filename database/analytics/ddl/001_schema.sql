BEGIN;

CREATE TABLE customers (
    id BIGSERIAL PRIMARY KEY,

    name VARCHAR(255) NOT NULL,

    segment VARCHAR(50) NOT NULL
        CHECK (
            segment IN (
                'smb',
                'mid_market',
                'enterprise'
            )
        ),

    country VARCHAR(100) NOT NULL,

    city VARCHAR(100),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE products (
    id BIGSERIAL PRIMARY KEY,

    sku VARCHAR(100) NOT NULL UNIQUE,

    name VARCHAR(255) NOT NULL,

    category VARCHAR(100) NOT NULL,

    price NUMERIC(14,2) NOT NULL
        CHECK (price >= 0),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE orders (
    id BIGSERIAL PRIMARY KEY,

    customer_id BIGINT NOT NULL
        REFERENCES customers(id),

    status VARCHAR(50) NOT NULL
        CHECK (
            status IN (
                'pending',
                'completed',
                'cancelled',
                'refunded'
            )
        ),

    total NUMERIC(14,2) NOT NULL
        CHECK (total >= 0),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE order_items (
    id BIGSERIAL PRIMARY KEY,

    order_id BIGINT NOT NULL
        REFERENCES orders(id)
        ON DELETE CASCADE,

    product_id BIGINT NOT NULL
        REFERENCES products(id),

    quantity INTEGER NOT NULL
        CHECK (quantity > 0),

    unit_price NUMERIC(14,2) NOT NULL
        CHECK (unit_price >= 0),

    UNIQUE (order_id, product_id)
);

COMMIT;