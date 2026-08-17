"""Tests de integracion MCP: carga de tools desde servidores MCP.

Gated: requiere servidores MCP levantados (mcp-glossary + mcp-explorer).
Skip si no hay URLs configuradas o los servers no responden.
"""

import os

import pytest


@pytest.mark.integration
async def test_mcp_client_loads_glossary_tools():
    """El cliente MCP carga tools/recursos desde el glossary server."""
    if not os.environ.get("MCP_GLOSSARY_URL"):
        pytest.skip("MCP_GLOSSARY_URL no configurada")

    from mcp_servers.client import build_mcp_client

    client = build_mcp_client()

    if "business-glossary" not in client.connections:
        pytest.skip("glossary server no configurado")

    try:
        tools = await client.get_tools()
    except Exception as exc:
        pytest.skip(f"glossary server no disponible: {exc}")

    tool_names = {t.name for t in tools}
    assert len(tools) > 0, "No se cargaron tools del glossary"


@pytest.mark.integration
async def test_mcp_client_loads_explorer_tools():
    """El cliente MCP carga tools desde el explorer server."""
    if not os.environ.get("MCP_EXPLORER_URL"):
        pytest.skip("MCP_EXPLORER_URL no configurada")

    from mcp_servers.client import build_mcp_client

    client = build_mcp_client()

    if "analytics-explorer" not in client.connections:
        pytest.skip("explorer server no configurado")

    try:
        tools = await client.get_tools()
    except Exception as exc:
        pytest.skip(f"explorer server no disponible: {exc}")

    tool_names = {t.name for t in tools}
    assert "list_tables" in tool_names or "describe_table" in tool_names


@pytest.mark.integration
async def test_mcp_client_loads_all_servers():
    """El cliente MCP carga tools de todos los servers configurados."""
    from mcp_servers.client import build_mcp_client

    client = build_mcp_client()

    if not client.connections:
        pytest.skip("no hay servidores MCP configurados")

    try:
        tools = await client.get_tools()
    except Exception as exc:
        pytest.skip(f"servidores MCP no disponibles: {exc}")

    assert len(tools) > 0, "No se cargaron tools de ningun server"


@pytest.mark.integration
async def test_load_mcp_tools_safely_returns_empty_without_servers():
    """Sin servers configurados, load_mcp_tools_safely devuelve []."""
    from mcp_servers.client import load_mcp_tools_safely

    # Guardar y limpiar env vars
    saved = {}
    for key in ("MCP_GLOSSARY_URL", "MCP_EXPLORER_URL", "MCP_FILESYSTEM_URL", "MCP_WEBSEARCH_URL"):
        saved[key] = os.environ.pop(key, None)

    try:
        tools = await load_mcp_tools_safely()
        assert tools == []
    finally:
        for key, val in saved.items():
            if val is not None:
                os.environ[key] = val