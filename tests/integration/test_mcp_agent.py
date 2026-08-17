"""Tests end-to-end del agente con bifurcacion SQL | MCP.

Gated por RUN_AGENT=1 + LLM + DB + servidores MCP.
Verifica que:
  - Pregunta SQL -> pipeline determinista (generated_sql presente)
  - Pregunta MCP -> loop reactivo (answer presente, sin generated_sql)
"""

import os

import pytest


@pytest.mark.integration
@pytest.mark.agent
async def test_agent_sql_question_uses_pipeline(full_stack):
    """Una pregunta de analytics va por el pipeline SQL."""
    from app.agent.graph import build_graph

    graph = build_graph()

    result = await graph.ainvoke(
        {
            "question": "¿Cuanto revenue hubo en julio?",
            "user_id": "test-mcp",
            "thread_id": "test-mcp-sql",
            "retry_count": 0,
        }
    )

    assert result.get("answer"), "Sin respuesta"
    assert result.get("generated_sql"), "Deberia generar SQL para pregunta SQL"
    assert result.get("question_type") == "sql"


@pytest.mark.integration
@pytest.mark.agent
async def test_agent_classifies_correctly(full_stack):
    """El clasificador distingue SQL de MCP."""
    from app.agent.routing import classify_question

    assert classify_question({"question": "¿Cuanto revenue hubo?"})["question_type"] == "sql"
    assert classify_question({"question": "Busca en la web"})["question_type"] == "mcp"


@pytest.mark.integration
@pytest.mark.agent
async def test_agent_sql_pipeline_preserved(full_stack):
    """El pipeline SQL sigue funcionando con grafo hibrido (sin MCP tools)."""
    from app.agent.graph import build_graph

    graph = build_graph(mcp_tools=[])

    result = await graph.ainvoke(
        {
            "question": "¿Cual fue el ticket promedio?",
            "user_id": "test-mcp",
            "thread_id": "test-mcp-pipeline",
            "retry_count": 0,
        }
    )

    assert result.get("answer"), "Sin respuesta"
    assert result.get("success") is True


@pytest.mark.integration
@pytest.mark.agent
async def test_agent_mcp_question_with_tools(full_stack):
    """Una pregunta no-SQL con tools MCP va por el loop reactivo."""
    if not os.environ.get("MCP_GLOSSARY_URL") and not os.environ.get("MCP_EXPLORER_URL"):
        pytest.skip("servidores MCP no configurados")

    from mcp_servers.client import load_mcp_tools_safely

    mcp_tools = await load_mcp_tools_safely()

    if not mcp_tools:
        pytest.skip("no se cargaron tools MCP")

    from app.agent.graph import build_graph

    graph = build_graph(mcp_tools=mcp_tools)

    result = await graph.ainvoke(
        {
            "question": "Lista las tablas disponibles en la base de datos",
            "user_id": "test-mcp",
            "thread_id": "test-mcp-loop",
            "retry_count": 0,
        }
    )

    assert result.get("answer"), "Sin respuesta del loop MCP"


@pytest.mark.integration
@pytest.mark.agent
async def test_ask_analytics_mcp_server_tool(full_stack):
    """La tool ask_analytics del servidor MCP del agente funciona."""
    from app.api.mcp_server import create_mcp_server, set_graph
    from app.agent.graph import build_graph

    graph = build_graph()
    set_graph(graph)

    server = create_mcp_server()

    import asyncio

    async def _call():
        return await server.call_tool(
            "ask_analytics", {"question": "¿Cuanto revenue hubo en julio?"}
        )

    content, _ = asyncio.run(_call())
    text = content[0].text

    assert "revenue" in text.lower() or "52500" in text