CREATE INDEX idx_orders_customer_id
    ON orders(customer_id);

CREATE INDEX idx_orders_created_at
    ON orders(created_at);

CREATE INDEX idx_orders_status
    ON orders(status);

CREATE INDEX idx_orders_status_created_at
    ON orders(status, created_at);

CREATE INDEX idx_order_items_order_id
    ON order_items(order_id);

CREATE INDEX idx_order_items_product_id
    ON order_items(product_id);

CREATE INDEX idx_customers_country
    ON customers(country);

CREATE INDEX idx_customers_segment
    ON customers(segment);

CREATE INDEX idx_products_category
    ON products(category);