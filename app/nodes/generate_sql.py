# app/nodes/generate_sql.py

from app.infrastructure.llm import get_llm


SYSTEM_PROMPT = """
Eres un experto en PostgreSQL y análisis de datos.

Tu tarea es convertir preguntas de negocio en SQL PostgreSQL.

REGLAS OBLIGATORIAS:

1. Solo puedes generar consultas de lectura.
2. La consulta final debe ser SELECT o WITH ... SELECT.
3. Nunca uses INSERT, UPDATE, DELETE, DROP, ALTER, CREATE,
   TRUNCATE, GRANT, REVOKE, COPY o CALL.
4. Usa únicamente tablas y columnas presentes en el esquema proporcionado.
5. Usa las relaciones indicadas en el esquema.
6. Para revenue, considera únicamente órdenes completed.
7. Evita SELECT *.
8. Incluye LIMIT 100 salvo que la consulta sea una agregación
   que naturalmente produzca pocas filas.
9. No inventes tablas ni columnas.
10. Devuelve únicamente SQL válido.
11. No uses Markdown.
12. No incluyas explicaciones.

Si la pregunta no puede responderse con el esquema disponible,
devuelve exactamente:

CANNOT_ANSWER
"""


async def generate_sql(state):
    llm = get_llm("analyst-smart")

    prompt = f"""
ESQUEMA DISPONIBLE:

{state["schema_context"]}

PREGUNTA DEL USUARIO:

{state["question"]}

Genera la consulta PostgreSQL.
"""

    response = await llm.ainvoke(
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

    sql = response.content.strip()

    if sql.startswith("```"):
        sql = (
            sql.replace("```sql", "")
            .replace("```SQL", "")
            .replace("```", "")
            .strip()
        )

    return {
        "generated_sql": sql,
    }