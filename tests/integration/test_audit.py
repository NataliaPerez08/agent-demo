import pytest

from app.infrastructure.audit import log_query


@pytest.mark.integration
async def test_audit_insert_and_read(agent_db_ready):
    entry = {
        "user_id": "audit-test-user",
        "thread_id": "audit-test-thread",
        "question": "pregunta de prueba",
        "generated_sql": "SELECT 1;",
        "successful": True,
        "error": None,
        "execution_ms": 12,
        "row_count": 1,
        "model": "analyst-smart",
        "retry_count": 0,
    }

    await log_query(entry)

    async with agent_db_ready.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT user_id, question, successful, row_count
                FROM analytics_query_log
                WHERE thread_id = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                ("audit-test-thread",),
            )
            row = await cur.fetchone()

    assert row is not None
    assert row[0] == "audit-test-user"
    assert row[1] == "pregunta de prueba"
    assert row[2] is True
    assert row[3] == 1


@pytest.mark.integration
async def test_audit_logs_failure(agent_db_ready):
    entry = {
        "user_id": "audit-test-user",
        "thread_id": "audit-test-thread-fail",
        "question": "pregunta que falla",
        "generated_sql": "DELETE FROM orders;",
        "successful": False,
        "error": "Operacion SQL no permitida: Delete",
        "execution_ms": 3,
        "row_count": 0,
        "model": "analyst-smart",
        "retry_count": 2,
    }

    await log_query(entry)

    async with agent_db_ready.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT successful, error, retry_count
                FROM analytics_query_log
                WHERE thread_id = %s
                """,
                ("audit-test-thread-fail",),
            )
            row = await cur.fetchone()

    assert row is not None
    assert row[0] is False
    assert row[1] == "Operacion SQL no permitida: Delete"
    assert row[2] == 2