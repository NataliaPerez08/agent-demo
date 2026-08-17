import pytest

from app.nodes.validate_sql import validate_sql


VALID_CASES = [
    "SELECT id FROM customers LIMIT 10;",
    "WITH x AS (SELECT 1) SELECT * FROM x;",
    "SELECT c.name, SUM(o.total) FROM customers c JOIN orders o ON o.customer_id = c.id GROUP BY c.name;",
    "SELECT * FROM completed_orders LIMIT 5;",
    "SELECT * FROM customer_revenue LIMIT 5;",
    "SELECT * FROM product_sales LIMIT 5;",
    "SELECT * FROM order_items LIMIT 5;",
    "SELECT * FROM products LIMIT 5;",
]

INVALID_CASES = [
    ("DELETE FROM orders;", "delete"),
    ("UPDATE customers SET name = 'x';", "update"),
    ("INSERT INTO orders VALUES (1, 1, 'pending', 10);", "insert"),
    ("DROP TABLE orders;", "drop"),
    ("CREATE TABLE t (id int);", "create"),
    ("TRUNCATE orders;", "truncatetable"),
    ("COPY orders TO '/tmp/a';", "copy"),
    ("SELECT 1; SELECT 2;", "sentencia"),
    ("SELECT * FROM information_schema.tables;", "information_schema"),
    ("SELECT * FROM pg_catalog.pg_tables;", "pg_catalog"),
    ("SELECT pg_sleep(5);", "pg_sleep"),
    ("SELECT * FROM secret_table;", "no permitida"),
    ("SELECT * FROM users;", "no permitida"),
    ("SELECT * FROM pg_shadow;", "no permitida"),
]


@pytest.mark.parametrize("sql", VALID_CASES)
async def test_valid_sql(sql):
    result = await validate_sql({"generated_sql": sql})
    assert result["sql_valid"] is True, result.get("validation_error")


@pytest.mark.parametrize("sql, expected", INVALID_CASES)
async def test_invalid_sql(sql, expected):
    result = await validate_sql({"generated_sql": sql})
    assert result["sql_valid"] is False
    assert result["validation_error"] is not None
    assert expected.lower() in result["validation_error"].lower()


async def test_empty_sql():
    result = await validate_sql({"generated_sql": ""})
    assert result["sql_valid"] is False


async def test_cannot_answer():
    result = await validate_sql({"generated_sql": "CANNOT_ANSWER"})
    assert result["sql_valid"] is False
    assert "no puede responderse" in result["validation_error"].lower()