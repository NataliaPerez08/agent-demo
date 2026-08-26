"""Chatbot Chainlit para el Data Analyst Agent.

Flujo:
  1. Usuario escribe una pregunta
  2. Chainlit llama a POST /chat del API
  3. Muestra la respuesta, el SQL generado, el chart plotly y los datos

Arrancar:
  chainlit run chatbot/app.py --port 8001
"""

import chainlit as cl
import plotly.graph_objects as go
from chainlit.input_widget import Select

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

    models = await client.get_models()
    available = [m for m in models if m.get("available")]

    model_names = [m["name"] for m in models]
    model_labels = {m["name"]: m["label"] for m in models}

    if available:
        default_model = available[0]["name"]
    else:
        default_model = "analyst-smart"

    cl.user_session.set("models", models)
    cl.user_session.set("model_labels", model_labels)
    cl.user_session.set("model", default_model)

    initial_index = model_names.index(default_model) if default_model in model_names else 0

    await cl.ChatSettings(
        [
            Select(
                id="model",
                label="Modelo",
                values=model_names,
                initial_index=initial_index,
            ),
        ]
    ).send()

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


@cl.on_settings_update
async def on_settings_update(settings: dict):
    """Actualiza el modelo seleccionado."""
    cl.user_session.set("model", settings.get("model", "analyst-smart"))


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
    model = cl.user_session.get("model")

    async with cl.Step(name="analizando") as step:

        step.output = f"Preguntando al agente: {question}"

        try:

            result = await client.chat(question, model=model)

        except Exception as exc:

            await cl.Message(
                content=f"❌ Error al contactar al agente: {exc}"
            ).send()
            return

    thread_id = result.get("thread_id")
    answer = result.get("answer", "")
    sql = result.get("sql")
    chart = result.get("chart")
    rows = result.get("rows")

    cl.user_session.set("thread_id", thread_id)


    if sql and sql != "CANNOT_ANSWER":

        sql_block = f"\n\n```sql\n{sql}\n```"
    else:
        sql_block = ""

    chart_element = None
    if chart and rows:
        fig = _build_plotly_chart(chart, rows)
        if fig:
            chart_element = cl.Plotly(
                name="chart",
                figure=fig,
                display="inline",
                size="large",
            )

    rows_table = ""
    if rows:
        rows_table = "\n\n" + _rows_to_markdown_table(rows)

    msg = cl.Message(content=answer + sql_block + rows_table)
    if chart_element:
        msg.elements = [chart_element]
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


def _build_plotly_chart(chart_config: dict, rows: list[dict]) -> go.Figure | None:
    """Construye un grafico Plotly interactivo desde el chart_config y los rows."""

    if not chart_config or not rows:
        return None

    chart_type = chart_config.get("type")
    title = chart_config.get("title", "Resultados")
    x_col = chart_config.get("x")
    y_col = chart_config.get("y")
    series_cols = chart_config.get("series")

    x_data = [row.get(x_col) for row in rows] if x_col else None
    y_data = [row.get(y_col) for row in rows] if y_col else None

    fig = go.Figure()

    if chart_type == "bar":
        if series_cols:
            for col in series_cols:
                series_y = [row.get(col) for row in rows]
                fig.add_trace(go.Bar(
                    name=col,
                    x=x_data,
                    y=series_y,
                ))
            fig.update_layout(barmode="group")
        else:
            fig.add_trace(go.Bar(x=x_data, y=y_data))

    elif chart_type == "line":
        if series_cols:
            for col in series_cols:
                series_y = [row.get(col) for row in rows]
                fig.add_trace(go.Scatter(
                    name=col,
                    x=x_data,
                    y=series_y,
                    mode="lines+markers",
                ))
        else:
            fig.add_trace(go.Scatter(
                x=x_data,
                y=y_data,
                mode="lines+markers",
            ))

    elif chart_type == "pie":
        fig.add_trace(go.Pie(labels=x_data, values=y_data))

    else:
        return None

    fig.update_layout(
        title=title,
        autosize=True,
        height=400,
        template="plotly_white",
        showlegend=bool(series_cols),
    )

    return fig


def _rows_to_markdown_table(rows: list[dict], max_rows: int = 30) -> str:
    """Convierte una lista de dicts a una tabla markdown."""

    if not rows:
        return ""

    headers = list(rows[0].keys())

    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    for row in rows[:max_rows]:
        values = [str(row.get(h, "")) for h in headers]
        lines.append("| " + " | ".join(values) + " |")

    if len(rows) > max_rows:
        lines.append(f"\n*Mostrando {max_rows} de {len(rows)} filas*")

    return "\n".join(lines)
