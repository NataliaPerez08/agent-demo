"""Servidor MCP que expone el data analyst agent como una tool MCP.

Tool expuesta:
  ask_analytics(question: str) -> str
    Recibe una pregunta en lenguaje natural, la procesa a traves del
    grafo LangGraph del agente (pipeline SQL o loop MCP) y devuelve
    la respuesta + el SQL generado.

Montado como endpoint /mcp (streamable HTTP) en la app FastAPI.
Clientes MCP como Claude Desktop pueden consumir esta tool para
usar el data analyst agent como una capability mas.

Uso desde un cliente MCP:
  URL: http://<host>:8000/mcp
  Transport: streamable-http
"""

import uuid

from mcp.server.fastmcp import FastMCP

# Holder del grafo: se setea desde el lifespan de FastAPI.
_graph = None


def set_graph(graph) -> None:
    """Setea el grafo del agente (llamado desde el lifespan)."""

    global _graph
    _graph = graph


def get_graph():
    """Devuelve el grafo del agente (o None si no esta listo)."""

    return _graph


def create_mcp_server() -> FastMCP:
    """Construye el FastMCP server que expone ask_analytics."""

    mcp = FastMCP(
        "data-analyst-agent",
        instructions=(
            "Servidor MCP que expone el data analyst agent. "
            "La tool ask_analytics recibe preguntas de negocio en "
            "lenguaje natural sobre datos de ventas y devuelve "
            "respuestas basadas en la analytics DB read-only."
        ),
    )

    @mcp.tool()
    async def ask_analytics(question: str) -> str:
        """Responde una pregunta de negocio sobre los datos analiticos.

        Args:
            question: Pregunta en lenguaje natural (ej. "¿Cuanto
                revenue hubo en julio?").

        Returns:
            La respuesta del agente, incluyendo el SQL generado
            cuando aplica.
        """

        graph = get_graph()

        if graph is None:
            return "El agente no esta listo aún."

        thread_id = f"mcp-{uuid.uuid4()}"

        config = {"configurable": {"thread_id": thread_id}}

        initial_state = {
            "question": question,
            "user_id": "mcp-client",
            "thread_id": thread_id,
            "retry_count": 0,
        }

        try:

            result = await graph.ainvoke(initial_state, config=config)

        except Exception as exc:

            return f"Error al procesar la pregunta: {exc}"

        answer = result.get("answer", "")
        sql = result.get("generated_sql")

        if sql and sql != "CANNOT_ANSWER":
            return f"{answer}\n\nSQL:\n{sql}"

        return answer

    return mcp


# Instancia lista para montar como ASGI.
mcp_server = create_mcp_server()