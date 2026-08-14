import json

from app.infrastructure.llm import get_llm


SYSTEM_PROMPT = """
Eres un analista de datos empresariales.

A partir de la pregunta del usuario, el SQL ejecutado y los resultados,
debes producir un analisis tecnico de los datos.

REGLAS:

1. Identifica tendencias, rankings y diferencias.
2. No inventes datos: usa unicamente los resultados proporcionados.
3. Si la muestra es pequena, senalalo.
4. Separa hechos de inferencias.
5. No afirmes causalidad sin evidencia.
6. No redactes la respuesta final al usuario: \
genera el analisis interno que alimenta esa respuesta.
7. Responde en español.
"""


async def analyze_results(state):

    question = state["question"]
    sql = state["generated_sql"]
    results = state.get("query_result", [])
    truncated = state.get("result_truncated", False)

    if not results:

        return {"analysis": "La consulta no devolvio resultados."}

    llm = get_llm("analyst-smart")

    payload = json.dumps(
        results,
        ensure_ascii=False,
        default=str,
    )

    prompt = f"""
PREGUNTA:

{question}

SQL EJECUTADO:

{sql}

RESULTADOS (truncated={truncated}, rows={len(results)}):

{payload}

Genera el analisis.
"""

    response = await llm.ainvoke(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
    )

    return {"analysis": response.content.strip()}