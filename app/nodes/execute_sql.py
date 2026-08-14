import time

from psycopg.rows import dict_row

from app.infrastructure.postgres import analytics_pool


MAX_ROWS = 100
STATEMENT_TIMEOUT_MS = 5000


async def execute_sql(state):

    sql = state["generated_sql"]

    start = time.perf_counter()

    try:

        async with analytics_pool.connection() as conn:

            async with conn.cursor(row_factory=dict_row) as cursor:

                await cursor.execute(
                    f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}"
                )

                await cursor.execute(sql)

                rows = await cursor.fetchmany(MAX_ROWS + 1)

    except Exception as exc:

        elapsed_ms = int((time.perf_counter() - start) * 1000)

        return {
            "query_result": [],
            "result_truncated": False,
            "execution_error": str(exc),
            "execution_ms": elapsed_ms,
        }

    elapsed_ms = int((time.perf_counter() - start) * 1000)

    truncated = len(rows) > MAX_ROWS

    if truncated:

        rows = rows[:MAX_ROWS]

    return {
        "query_result": rows,
        "result_truncated": truncated,
        "execution_error": None,
        "execution_ms": elapsed_ms,
    }