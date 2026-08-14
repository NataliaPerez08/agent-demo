from app.infrastructure.postgres import analytics_pool


SCHEMA_QUERY = """
SELECT
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY
    table_name,
    ordinal_position;
"""

RELATIONSHIP_QUERY = """
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name

FROM information_schema.table_constraints tc

JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema

JOIN information_schema.constraint_column_usage ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema

WHERE
    tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_schema = 'public';
"""

async def retrieve_schema(state):

    async with analytics_pool.connection() as conn:

        async with conn.cursor() as cursor:

            await cursor.execute(SCHEMA_QUERY)

            rows = await cursor.fetchall()

    schema: dict[str, list[str]] = {}

    for row in rows:

        table_name = row[0]
        column_name = row[1]
        data_type = row[2]
        nullable = row[3]

        schema.setdefault(
            table_name,
            []
        ).append(
            f"{column_name} {data_type} nullable={nullable}"
        )

    parts = []

    for table, columns in schema.items():

        parts.append(
            f"""
TABLE {table}
{chr(10).join(columns)}
"""
        )

    return {
        "schema_context": "\n".join(parts)
    }