from app.infrastructure.llm import ainvoke_with_usage, get_llm


MAX_RETRIES = 2


SYSTEM_PROMPT = """
Eres un experto en PostgreSQL encargado de corregir consultas SQL que fallaron.

Recibiras:

- La pregunta original del usuario.
- El esquema disponible.
- El SQL que fallo.
- El mensaje de error.

REGLAS OBLIGATORIAS:

1. Devuelve unicamente SQL valido compatible con PostgreSQL.
2. Solo consultas de lectura (SELECT o WITH ... SELECT).
3. Usa unicamente tablas y columnas del esquema.
4. No uses Markdown ni explicaciones.
5. Si el error indica que la pregunta no puede responderse, \
devuelve exactamente: CANNOT_ANSWER
"""


def _strip_markdown(sql: str) -> str:

    if sql.startswith("```"):

        sql = (
            sql.replace("```sql", "")
            .replace("```SQL", "")
            .replace("```", "")
            .strip()
        )

    return sql.strip()


async def fix_sql(state):

    retry = state.get("retry_count", 0)

    error = (
        state.get("validation_error")
        or state.get("execution_error")
        or "error desconocido"
    )

    llm = get_llm("analyst-smart")

    prompt = f"""
ESQUEMA DISPONIBLE:

{state.get("schema_context", "")}

PREGUNTA DEL USUARIO:

{state["question"]}

SQL QUE FALLO:

{state.get("generated_sql", "")}

ERROR:

{error}

Corrige la consulta SQL.
"""

    response = await ainvoke_with_usage(
        llm,
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    sql = _strip_markdown(response)

    return {
        "generated_sql": sql,
        "retry_count": retry + 1,
        "validation_error": None,
        "execution_error": None,
    }