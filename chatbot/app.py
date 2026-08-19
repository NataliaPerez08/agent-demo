"""Chatbot Chainlit para el Data Analyst Agent.

Flujo:
  1. Usuario escribe una pregunta
  2. Chainlit llama a POST /chat del API
  3. Muestra la respuesta, el SQL generado y el chart sugerido
  4. Botones para exportar CSV/Excel del ultimo resultado

Arrancar:
  chainlit run chatbot/app.py --port 8001
"""

import json

import chainlit as cl

from chatbot.agent_client import AgentClient


def get_client() -> AgentClient:
    """Crea un AgentClient desde la config de Chainlit."""

    import os

    base_url = os.environ.get("AGENT_API_URL", "http://localhost:8000")
    return AgentClient(base_url)


@cl.on_chat_start
async def on_chat_start():
    """Inicializa la sesion y guarda el thread_id."""

    client = get_client()

    ready = await client.health()

    if not ready:
        await cl.Message(
            content=(
                "⚠️ El API del agente no esta disponible. "
                "Verifica que el backend este corriendo en "
                f"`{client.base_url}`."
            )
        ).send()
        return

    cl.user_session.set("client", client)
    cl.user_session.set("thread_id", None)

    await cl.Message(
        content=(
            "¡Hola! Soy el Data Analyst Agent. "
            "Preguntame sobre tus datos de ventas:\n\n"
            "- ¿Cuanto revenue hubo en julio?\n"
            "- ¿Cuales fueron los 5 clientes con mas revenue?\n"
            "- ¿Que pais genero mas revenue?\n"
            "- Compara junio contra julio."
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """Procesa cada mensaje del usuario."""

    client: AgentClient = cl.user_session.get("client")

    if client is None:
        await cl.Message(
            content="El API no esta disponible. Reinicia el chat."
        ).send()
        return

    question = message.content

    async with cl.Step(name="analizando") as step:

        step.output = f"Preguntando al agente: {question}"

        try:

            result = await client.chat(question)

        except Exception as exc:

            await cl.Message(
                content=f"❌ Error al contactar al agente: {exc}"
            ).send()
            return

    thread_id = result.get("thread_id")
    answer = result.get("answer", "")
    sql = result.get("sql")
    chart = result.get("chart")

    cl.user_session.set("thread_id", thread_id)

    elements = []

    if sql and sql != "CANNOT_ANSWER":

        sql_block = f"\n\n```sql\n{sql}\n```"
    else:
        sql_block = ""

    if chart:

        chart_text = _format_chart(chart)
        chart_block = f"\n\n---\n\n{chart_text}"
    else:
        chart_block = ""

    msg = cl.Message(content=answer + sql_block + chart_block)
    await msg.send()

    if thread_id:

        actions = [
            cl.Action(
                name="export_csv",
                value=thread_id,
                label="📊 Exportar CSV",
            ),
            cl.Action(
                name="export_xlsx",
                value=thread_id,
                label="📈 Exportar Excel",
            ),
        ]
        await cl.Message(
            content="Descargar resultados:",
            actions=actions,
        ).send()


@cl.action_callback("export_csv")
async def on_export_csv(action: cl.Action):

    thread_id = action.value
    client: AgentClient = cl.user_session.get("client")

    try:

        data = await client.export_csv(thread_id)

        file = cl.File(
            name=f"results_{thread_id[:8]}.csv",
            content=data,
            mime="text/csv",
        )
        await cl.Message(content="CSV listo:", elements=[file]).send()

    except Exception as exc:
        await cl.Message(content=f"Error al exportar: {exc}").send()


@cl.action_callback("export_xlsx")
async def on_export_xlsx(action: cl.Action):

    thread_id = action.value
    client: AgentClient = cl.user_session.get("client")

    try:

        data = await client.export_excel(thread_id)

        file = cl.File(
            name=f"results_{thread_id[:8]}.xlsx",
            content=data,
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
        )
        await cl.Message(content="Excel listo:", elements=[file]).send()

    except Exception as exc:
        await cl.Message(content=f"Error al exportar: {exc}").send()


def _format_chart(chart: dict) -> str:

    chart_type = chart.get("type", "unknown")
    title = chart.get("title", "")
    x = chart.get("x")
    y = chart.get("y")

    lines = [f"**Tipo:** {chart_type}", f"**Titulo:** {title}"]

    if x:
        lines.append(f"**Eje X:** {x}")
    if y:
        lines.append(f"**Eje Y:** {y}")

    return "\n".join(lines)