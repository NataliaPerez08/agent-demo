"""Tests del servidor MCP que expone el agente como tool ask_analytics.

Probado in-process (sin red ni Docker):
- La tool ask_analytics se registra correctamente
- ask_analytics devuelve respuesta cuando el grafo esta seteado
- ask_analytics maneja el caso de grafo no listo
- ask_analytics propaga el SQL cuando aplica
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest


def test_mcp_server_builds():
    from app.api.mcp_server import create_mcp_server

    server = create_mcp_server()
    assert server.name == "data-analyst-agent"


def test_ask_analytics_tool_registered():
    import asyncio

    from app.api.mcp_server import create_mcp_server

    server = create_mcp_server()

    async def _get():
        return await server.list_tools()

    tools = asyncio.run(_get())
    names = {t.name for t in tools}

    assert "ask_analytics" in names


def test_ask_analytics_graph_not_ready():
    import asyncio

    from app.api.mcp_server import create_mcp_server, get_graph, set_graph

    set_graph(None)
    server = create_mcp_server()

    async def _call():
        return await server.call_tool("ask_analytics", {"question": "test"})

    content, _ = asyncio.run(_call())
    text = content[0].text
    assert "no esta listo" in text


def test_ask_analytics_with_mock_graph():
    import asyncio

    from app.api.mcp_server import create_mcp_server, set_graph

    fake_graph = AsyncMock()
    fake_graph.ainvoke = AsyncMock(
        return_value={
            "answer": "El revenue fue 52500.",
            "generated_sql": "SELECT SUM(total) FROM orders WHERE status = 'completed'",
        }
    )

    set_graph(fake_graph)
    server = create_mcp_server()

    async def _call():
        return await server.call_tool(
            "ask_analytics", {"question": "¿Cuanto revenue hubo en julio?"}
        )

    content, _ = asyncio.run(_call())
    text = content[0].text

    assert "52500" in text
    assert "SELECT SUM(total)" in text
    assert "SQL" in text

    fake_graph.ainvoke.assert_awaited_once()
    call_args = fake_graph.ainvoke.call_args
    state_arg = call_args.args[0]
    assert state_arg["question"] == "¿Cuanto revenue hubo en julio?"
    assert state_arg["user_id"] == "mcp-client"


def test_ask_analytics_no_sql_in_response():
    import asyncio

    from app.api.mcp_server import create_mcp_server, set_graph

    fake_graph = AsyncMock()
    fake_graph.ainvoke = AsyncMock(
        return_value={
            "answer": "No se pudo responder.",
            "generated_sql": "CANNOT_ANSWER",
        }
    )

    set_graph(fake_graph)
    server = create_mcp_server()

    async def _call():
        return await server.call_tool("ask_analytics", {"question": "x"})

    content, _ = asyncio.run(_call())
    text = content[0].text

    assert "No se pudo responder" in text
    assert "SQL" not in text


def test_ask_analytics_handles_graph_exception():
    import asyncio

    from app.api.mcp_server import create_mcp_server, set_graph

    fake_graph = AsyncMock()
    fake_graph.ainvoke = AsyncMock(side_effect=RuntimeError("DB down"))

    set_graph(fake_graph)
    server = create_mcp_server()

    async def _call():
        return await server.call_tool("ask_analytics", {"question": "x"})

    content, _ = asyncio.run(_call())
    text = content[0].text

    assert "Error" in text
    assert "DB down" in text