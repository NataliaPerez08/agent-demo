from pathlib import Path

import yaml

from app.infrastructure.postgres import analytics_pool
from app.infrastructure.redis import cache_get, cache_set

SCHEMA_CACHE_KEY = "schema:analytics"
SCHEMA_CACHE_TTL = 3600

DICT_PATH = (
    Path(__file__).resolve().parents[2]
    / "database"
    / "analytics"
    / "model"
    / "data_dictionary.yaml"
)

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

PRIMARY_KEY_QUERY = """
SELECT
    tc.table_name,
    kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
WHERE
    tc.constraint_type = 'PRIMARY KEY'
    AND tc.table_schema = 'public'
ORDER BY
    tc.table_name,
    kcu.ordinal_position;
"""


def _load_data_dictionary() -> dict:
    """Carga el data_dictionary.yaml desde el filesystem."""

    try:
        with open(DICT_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _format_business_rules(data: dict) -> list[str]:
    """Extrae las business rules del data_dictionary como lineas de texto."""

    rules = data.get("business_rules", {})
    if not rules:
        return []

    lines = ["", "BUSINESS RULES"]

    for name, spec in rules.items():
        desc = str(spec.get("description", "")).strip().replace("\n", " ")
        lines.append(f"- {name}: {desc}")

    return lines


async def retrieve_schema(state):

    cached = await cache_get(SCHEMA_CACHE_KEY)
    if cached:
        return {"schema_context": cached}

    async with analytics_pool.connection() as conn, conn.cursor() as cursor:

        await cursor.execute(SCHEMA_QUERY)

        rows = await cursor.fetchall()

        await cursor.execute(RELATIONSHIP_QUERY)

        rels = await cursor.fetchall()

        await cursor.execute(PRIMARY_KEY_QUERY)

        pks = await cursor.fetchall()

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

    if pks:

        pk_map: dict[str, list[str]] = {}

        for pk_table, pk_col in pks:
            pk_map.setdefault(pk_table, []).append(pk_col)

        pk_lines = ["", "PRIMARY KEYS"]

        for pk_table, pk_cols in pk_map.items():
            pk_lines.append(f"- {pk_table}: {', '.join(pk_cols)}")

        parts.append("\n".join(pk_lines))

    if rels:

        rel_lines = ["", "RELATIONSHIPS"]

        for r in rels:

            rel_lines.append(
                f"{r[0]}.{r[1]} -> {r[2]}.{r[3]}"
            )

        parts.append("\n".join(rel_lines))

    dict_data = _load_data_dictionary()
    business_lines = _format_business_rules(dict_data)

    if business_lines:
        parts.append("\n".join(business_lines))

    schema_context = "\n".join(parts)

    await cache_set(SCHEMA_CACHE_KEY, schema_context, SCHEMA_CACHE_TTL)

    return {
        "schema_context": schema_context
    }