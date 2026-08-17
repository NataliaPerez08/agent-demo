from psycopg.rows import dict_row

from app.infrastructure.postgres import agent_pool


CREATE_DASHBOARD_SQL = """
INSERT INTO dashboards (name, description, user_id)
VALUES (%s, %s, %s)
RETURNING id, name, description, user_id;
"""

GET_DASHBOARD_SQL = """
SELECT id, name, description, user_id
FROM dashboards
WHERE id = %s;
"""

LIST_DASHBOARDS_SQL = """
SELECT id, name, description, user_id
FROM dashboards
WHERE user_id = %s
ORDER BY created_at DESC;
"""

DELETE_DASHBOARD_SQL = """
DELETE FROM dashboards
WHERE id = %s
RETURNING id;
"""

CREATE_WIDGET_SQL = """
INSERT INTO dashboard_widgets (dashboard_id, title, question, chart_type, position)
VALUES (%s, %s, %s, %s, %s)
RETURNING id, dashboard_id, title, question, chart_type, position;
"""

LIST_WIDGETS_SQL = """
SELECT id, dashboard_id, title, question, chart_type, position
FROM dashboard_widgets
WHERE dashboard_id = %s
ORDER BY position;
"""

DELETE_WIDGET_SQL = """
DELETE FROM dashboard_widgets
WHERE id = %s AND dashboard_id = %s
RETURNING id;
"""


async def create_dashboard(name: str, description: str | None, user_id: str) -> dict | None:

    try:
        async with agent_pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    CREATE_DASHBOARD_SQL,
                    (name, description, user_id),
                )
                return await cur.fetchone()
    except Exception:
        return None


async def get_dashboard(dashboard_id: int) -> dict | None:

    try:
        async with agent_pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(GET_DASHBOARD_SQL, (dashboard_id,))
                dashboard = await cur.fetchone()
                if not dashboard:
                    return None
                await cur.execute(LIST_WIDGETS_SQL, (dashboard_id,))
                dashboard["widgets"] = await cur.fetchall()
                return dashboard
    except Exception:
        return None


async def list_dashboards(user_id: str) -> list[dict]:

    try:
        async with agent_pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(LIST_DASHBOARDS_SQL, (user_id,))
                return await cur.fetchall()
    except Exception:
        return []


async def delete_dashboard(dashboard_id: int) -> bool:

    try:
        async with agent_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(DELETE_DASHBOARD_SQL, (dashboard_id,))
                row = await cur.fetchone()
                return row is not None
    except Exception:
        return False


async def add_widget(
    dashboard_id: int,
    title: str,
    question: str,
    chart_type: str | None,
    position: int,
) -> dict | None:

    try:
        async with agent_pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    CREATE_WIDGET_SQL,
                    (dashboard_id, title, question, chart_type, position),
                )
                return await cur.fetchone()
    except Exception:
        return None


async def delete_widget(dashboard_id: int, widget_id: int) -> bool:

    try:
        async with agent_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(DELETE_WIDGET_SQL, (widget_id, dashboard_id))
                row = await cur.fetchone()
                return row is not None
    except Exception:
        return False