import json
import re

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

FORMATO DE RESPUESTA:

Debes responder SIEMPRE en formato JSON con esta estructura exacta:

{
  "can_answer": true,
  "sql": "SELECT ...",
  "reason": null
}

Si la pregunta no puede responderse:

{
  "can_answer": false,
  "sql": null,
  "reason": "El esquema no contiene ..."
}

No uses Markdown ni texto fuera del JSON.
"""


def _parse_json_response(raw: str) -> dict:

    text = raw.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return {"can_answer": True, "sql": raw.strip(), "reason": None}


def _strip_markdown(sql: str) -> str:

    if sql and sql.startswith("```"):
        sql = (
            sql.replace("```sql", "")
            .replace("```SQL", "")
            .replace("```", "")
            .strip()
        )

    return (sql or "").strip()


async def fix_sql(state):

    retry = state.get("retry_count", 0)

    error = (
        state.get("validation_error")
        or state.get("execution_error")
        or "error desconocido"
    )

    llm = get_llm(model=state.get("model"))

    prompt = f"""
ESQUEMA DISPONIBLE:

{state.get("schema_context", "")}

PREGUNTA DEL USUARIO:

{state["question"]}

SQL QUE FALLO:

{state.get("generated_sql", "")}

ERROR:

{error}

Corrige la consulta SQL en formato JSON.
"""

    response = await ainvoke_with_usage(
        llm,
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    parsed = _parse_json_response(response)

    if not parsed.get("can_answer", True):
        return {
            "generated_sql": "CANNOT_ANSWER",
            "retry_count": retry + 1,
            "validation_error": None,
            "execution_error": None,
        }

    sql = _strip_markdown(parsed.get("sql", ""))

    return {
        "generated_sql": sql,
        "retry_count": retry + 1,
        "validation_error": None,
        "execution_error": None,
    }