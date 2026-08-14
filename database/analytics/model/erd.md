# Analytics Data Model

```mermaid
erDiagram

    CUSTOMERS ||--o{ ORDERS : places

    ORDERS ||--|{ ORDER_ITEMS : contains

    PRODUCTS ||--o{ ORDER_ITEMS : appears_in


    CUSTOMERS {
        bigint id PK
        varchar name
        varchar segment
        varchar country
        varchar city
        timestamptz created_at
    }

    ORDERS {
        bigint id PK
        bigint customer_id FK
        varchar status
        numeric total
        timestamptz created_at
    }

    PRODUCTS {
        bigint id PK
        varchar sku
        varchar name
        varchar category
        numeric price
    }

    ORDER_ITEMS {
        bigint id PK
        bigint order_id FK
        bigint product_id FK
        integer quantity
        numeric unit_price
    }