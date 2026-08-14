import pytest

from app.nodes.execute_sql import execute_sql
from app.nodes.schema import retrieve_schema


INTEGRITY_QUERY = """
SELECT
    o.id,
    o.total,
    SUM(oi.quantity * oi.unit_price) AS calculated_total
FROM orders o
JOIN order_items oi
    ON oi.order_id = o.id
GROUP BY
    o.id,
    o.total
HAVING
    o.total <> SUM(oi.quantity * oi.unit_price);
"""


@pytest.mark.integration
async def test_connection(analytics_pool_ready):
    async with analytics_pool_ready.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1")
            row = await cur.fetchone()
            assert row[0] == 1


@pytest.mark.integration
async def test_schema_retrieval(analytics_pool_ready):
    state = await retrieve_schema({})
    context = state["schema_context"]

    for table in ("customers", "orders", "products", "order_items"):
        assert f"TABLE {table}" in context


@pytest.mark.integration
async def test_execute_select(analytics_pool_ready):
    state = await execute_sql({"generated_sql": "SELECT 1 AS one;"})

    assert state["execution_error"] is None
    assert state["query_result"] == [{"one": 1}]
    assert state["execution_ms"] >= 0
    assert state["result_truncated"] is False


@pytest.mark.integration
async def test_write_rejected_by_readonly_role(analytics_pool_ready):
    state = await execute_sql({"generated_sql": "DELETE FROM orders WHERE false;"})

    assert state["execution_error"] is not None
    assert "permission denied" in state["execution_error"].lower()


@pytest.mark.integration
async def test_statement_timeout(analytics_pool_ready):
    state = await execute_sql({"generated_sql": "SELECT pg_sleep(10);"})

    assert state["execution_error"] is not None
    lowered = state["execution_error"].lower()
    assert "timeout" in lowered or "cancel" in lowered


@pytest.mark.integration
async def test_seed_consistency(analytics_pool_ready):
    state = await execute_sql({"generated_sql": INTEGRITY_QUERY})

    assert state["execution_error"] is None, state["execution_error"]
    assert state["query_result"] == []


@pytest.mark.integration
async def test_max_rows_truncation(analytics_pool_ready):
    state = await execute_sql(
        {"generated_sql": "SELECT generate_series AS n FROM generate_series(1, 200);"}
    )

    assert state["execution_error"] is None
    assert state["result_truncated"] is True
    assert len(state["query_result"]) == 100