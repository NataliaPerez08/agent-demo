import hashlib
import json
import time

from psycopg.rows import dict_row

from app.infrastructure.postgres import analytics_pool
from app.infrastructure.redis import cache_get, cache_set

MAX_ROWS = 100
STATEMENT_TIMEOUT_MS = 5000
QUERY_CACHE_TTL = 300
QUERY_CACHE_PREFIX = "query:"


async def execute_sql(state):

    sql = state["generated_sql"]

    cache_key = QUERY_CACHE_PREFIX + hashlib.sha256(
        sql.encode()
    ).hexdigest()

    cached = await cache_get(cache_key)
    if cached:

        payload = json.loads(cached)

        return {
            "query_result": payload["rows"],
            "result_truncated": payload["truncated"],
            "execution_error": None,
            "execution_ms": 0,
        }

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

    await cache_set(
        cache_key,
        json.dumps(
            {"rows": rows, "truncated": truncated},
            default=str,
        ),
        QUERY_CACHE_TTL,
    )

    return {
        "query_result": rows,
        "result_truncated": truncated,
        "execution_error": None,
        "execution_ms": elapsed_ms,
    }