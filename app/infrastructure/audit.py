from app.infrastructure.postgres import agent_pool

INSERT_AUDIT_SQL = """
INSERT INTO analytics_query_log (
    request_id,
    user_id,
    thread_id,
    question,
    generated_sql,
    successful,
    error,
    execution_ms,
    row_count,
    model,
    retry_count
)
VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
"""


async def log_query(entry: dict) -> None:
    """Registra una ejecucion en analytics_query_log.

    Fail-open: un fallo de la auditoria no debe romper la respuesta
    al usuario. Solo registra; no devuelve nada.
    """

    try:

        async with agent_pool.connection() as conn, conn.cursor() as cursor:

            await cursor.execute(
                INSERT_AUDIT_SQL,
                (
                    entry.get("request_id"),
                    entry.get("user_id"),
                    entry.get("thread_id"),
                    entry.get("question"),
                    entry.get("generated_sql"),
                    bool(entry.get("successful", False)),
                    entry.get("error"),
                    int(entry.get("execution_ms", 0)),
                    int(entry.get("row_count", 0)),
                    entry.get("model"),
                    int(entry.get("retry_count", 0)),
                ),
            )

    except Exception:
        pass