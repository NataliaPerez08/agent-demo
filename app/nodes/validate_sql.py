import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

FORBIDDEN_EXPRESSIONS = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Create,
    exp.Alter,
    exp.TruncateTable,
    exp.Command,
    exp.Copy,
)

FORBIDDEN_FUNCTIONS = {
    "pg_sleep",
    "pg_terminate_backend",
    "pg_cancel_backend",
    "dblink",
    "dblink_exec",
    "lo_import",
    "lo_export",
}

FORBIDDEN_SCHEMAS = {
    "pg_catalog",
    "information_schema",
}

ALLOWED_TABLES = {
    "customers",
    "orders",
    "products",
    "order_items",
    "completed_orders",
    "customer_revenue",
    "product_sales",
}


def validate_ast(expression: exp.Expression) -> tuple[bool, str | None]:

    cte_names = {c.alias_or_name for c in expression.find_all(exp.CTE)}

    found_tables: set[str] = set()

    for node in expression.walk():

        if isinstance(node, FORBIDDEN_EXPRESSIONS):
            return (
                False,
                f"Operación SQL no permitida: {type(node).__name__}",
            )

        if isinstance(node, exp.Anonymous) and node.name.lower() in FORBIDDEN_FUNCTIONS:
            return (
                False,
                f"Función no permitida: {node.name}",
            )

        if isinstance(node, exp.Table):
            schema_name = (node.db or "").lower()
            if schema_name in FORBIDDEN_SCHEMAS:
                return (
                    False,
                    f"Acceso no permitido al esquema: {schema_name}",
                )

            table_name = (node.name or "").lower()
            if table_name and table_name not in cte_names and table_name not in found_tables:
                found_tables.add(table_name)

    for table in found_tables:
        if table not in ALLOWED_TABLES:
            return (
                False,
                f"Tabla no permitida: {table}. Solo se permiten: {', '.join(sorted(ALLOWED_TABLES))}.",
            )

    return True, None


async def validate_sql(state):

    sql = state.get("generated_sql", "").strip()

    if not sql:
        return {
            "sql_valid": False,
            "validation_error": "SQL vacío",
        }

    if sql == "CANNOT_ANSWER":
        return {
            "sql_valid": False,
            "validation_error": "La pregunta no puede responderse con el esquema.",
        }

    try:

        expressions = sqlglot.parse(
            sql,
            read="postgres",
        )

    except ParseError as exc:

        return {
            "sql_valid": False,
            "validation_error": f"SQL inválido: {exc}",
        }

    if len(expressions) != 1:

        return {
            "sql_valid": False,
            "validation_error": "Solo se permite una sentencia SQL.",
        }

    expression = expressions[0]

    valid, error = validate_ast(expression)

    if not valid:

        return {
            "sql_valid": False,
            "validation_error": error,
        }

    if not expression.find(exp.Select):

        return {
            "sql_valid": False,
            "validation_error": "La consulta debe contener SELECT.",
        }

    return {
        "sql_valid": True,
        "validation_error": None,
        "generated_sql": expression.sql(
            dialect="postgres",
            pretty=True,
        ),
    }