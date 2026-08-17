"""Cliente MCP del agente: carga tools de multiples servidores MCP
vía HTTP streamable.

Servidores:
  - business-glossary  : recursos semánticos (data_dictionary)   [propio]
  - analytics-explorer : tools de exploración de la analytics DB  [propio]
  - filesystem         : lectura de archivos/docs locales         [estándar]
  - websearch          : búsqueda web para datos externos          [estándar]

Los servers estándar (filesystem, websearch) se asumen desplegados
como servicios HTTP streamable externos. Si no están configurados,
se omiten silenciosamente (fail-open) para no bloquear el arranque.
"""

from __future__ import annotations

import os

from langchain_mcp_adapters.client import MultiServerMCPClient


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def build_mcp_client() -> MultiServerMCPClient:
    """Construye el cliente con los servers configurados via env.

    Variables (todas opcionales; las no configuradas se omiten):
      MCP_GLOSSARY_URL   -> http://mcp-glossary:8100/mcp
      MCP_EXPLORER_URL   -> http://mcp-explorer:8101/mcp
      MCP_FILESYSTEM_URL -> http://mcp-filesystem:8102/mcp
      MCP_WEBSEARCH_URL  -> http://mcp-websearch:8103/mcp
    """

    connections: dict[str, dict] = {}

    glossary_url = _env("MCP_GLOSSARY_URL")
    if glossary_url:
        connections["business-glossary"] = {
            "transport": "http",
            "url": glossary_url,
        }

    explorer_url = _env("MCP_EXPLORER_URL")
    if explorer_url:
        connections["analytics-explorer"] = {
            "transport": "http",
            "url": explorer_url,
        }

    filesystem_url = _env("MCP_FILESYSTEM_URL")
    if filesystem_url:
        connections["filesystem"] = {
            "transport": "http",
            "url": filesystem_url,
        }

    websearch_url = _env("MCP_WEBSEARCH_URL")
    if websearch_url:
        connections["websearch"] = {
            "transport": "http",
            "url": websearch_url,
        }

    return MultiServerMCPClient(connections)


async def load_mcp_tools_safely() -> list:
    """Carga tools de todos los servers MCP configurados.

    Fail-open: si no hay servers configurados o la carga falla,
    devuelve [] para que el agente arranque igual (modo pipeline-only).
    """

    client = build_mcp_client()

    if not client.connections:
        return []

    try:
        return await client.get_tools()
    except Exception:
        return []