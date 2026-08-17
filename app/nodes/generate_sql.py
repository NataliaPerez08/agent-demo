import json
import re

from app.infrastructure.llm import ainvoke_with_usage, get_llm


SYSTEM_PROMPT = """
Eres un experto en PostgreSQL y análisis de datos.

Tu tarea es convertir preguntas de negocio en SQL PostgreSQL.

REGLAS OBLIGATORIAS:

1. Solo puedes generar consultas de lectura.
2. La consulta final debe ser SELECT o WITH ... SELECT.
3. Nunca uses INSERT, UPDATE, DELETE, DROP, ALTER, CREATE,
   TRUNCATE, GRANT, REVOKE, COPY o CALL.
4. Usa únicamente las tablas y columnas presentes en el esquema.
5. Usa las relaciones indicadas en el esquema.
6. Para revenue, considera únicamente órdenes completed.
7. Evita SELECT *.
8. Incluye LIMIT 100 salvo que la consulta sea una agregación
   que naturalmente produzca pocas filas.
9. No inventes tablas ni columnas.

FORMATO DE RESPUESTA:

Debes responder SIEMPRE en formato JSON con esta estructura exacta:

{
  "can_answer": true,
  "sql": "SELECT ...",
  "reason": null
}

Si la pregunta no puede responderse con el esquema disponible:

{
  "can_answer": false,
  "sql": null,
  "reason": "El esquema no contiene información sobre ..."
}

No uses Markdown. No incluyas texto fuera del JSON.
"""


def _parse_json_response(raw: str) -> dict:
    """Extrae el JSON de la respuesta del LLM de forma tolerante.

    Maneja:
    - JSON puro
    - JSON envuelto en ```json ... ```
    - JSON con texto antes/después
    """

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


async def generate_sql(state):

    llm = get_llm()

    prompt = f"""
ESQUEMA DISPONIBLE:

{state["schema_context"]}

PREGUNTA DEL USUARIO:

{state["question"]}

Genera la consulta PostgreSQL en formato JSON.
"""

    response = await ainvoke_with_usage(
        llm,
        [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]
    )

    parsed = _parse_json_response(response)

    if not parsed.get("can_answer", True):
        return {
            "generated_sql": "CANNOT_ANSWER",
        }

    sql = _strip_markdown(parsed.get("sql", ""))

    return {
        "generated_sql": sql,
    }