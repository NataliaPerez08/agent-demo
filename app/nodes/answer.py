from app.infrastructure.llm import ainvoke_with_usage, get_llm


SYSTEM_PROMPT = """
Eres un asistente de business intelligence.

A partir del analisis interno de datos, redacta la respuesta final
al usuario que hizo la pregunta de negocio.

FORMATO RECOMENDADO:

1. Conclusion principal (1-2 frases).
2. Datos relevantes (lista breve).
3. Contexto / interpretacion (1 frase).

REGLAS:

1. Basate unicamente en el analisis proporcionado.
2. No inventes numeros.
3. Responde en español.
4. No menciones SQL ni detalles tecnicos.
"""


async def generate_answer(state):

    analysis = state.get("analysis", "")

    if not analysis:

        return {
            "answer": "No hay informacion suficiente para responder.",
            "success": True,
        }

    llm = get_llm("analyst-smart")

    prompt = f"""
PREGUNTA DEL USUARIO:

{state["question"]}

ANALISIS INTERNO:

{analysis}

Redacta la respuesta final al usuario.
"""

    response = await ainvoke_with_usage(
        llm,
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
    )

    return {"answer": response.strip(), "success": True}