"""Tests de los servidores MCP propios (in-process, sin red ni Docker).

business_glossary: probado directamente via read_resource (no requiere DB).
analytics_explorer: tools probadas via call_tool con pool mockeado.
"""

from unittest.mock import AsyncMock, MagicMock, patch


class _FakeAsyncCM:
    """Async context manager que devuelve un valor fijo."""

    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, *a):
        return None


def _make_fake_pool(fetchall_return, description=None):
    fake_cursor = AsyncMock()
    fake_cursor.fetchall = AsyncMock(return_value=fetchall_return)
    fake_cursor.execute = AsyncMock()
    fake_cursor.description = description or [("col1",), ("col2",)]

    fake_conn = MagicMock()
    fake_conn.cursor.return_value = _FakeAsyncCM(fake_cursor)

    async def _noop():
        pass

    fake_pool = MagicMock()
    fake_pool.open = _noop
    fake_pool.close = _noop
    fake_pool.connection = lambda: _FakeAsyncCM(fake_conn)

    return fake_pool


# ---- Business glossary (resources) ----


def test_business_glossary_server_builds():
    from mcp_servers.servers.business_glossary import create_server

    server = create_server()
    assert server.name == "business-glossary"


def test_business_glossary_resources_registered():
    import asyncio

    from mcp_servers.servers.business_glossary import create_server

    server = create_server()

    async def _get():
        return await server.list_resources()

    resources = asyncio.run(_get())
    uris = {str(r.uri) for r in resources}

    assert any("glossary://database" in u for u in uris)
    assert any("glossary://metrics" in u for u in uris)
    assert any("glossary://tables" in u for u in uris)


def test_business_glossary_database_overview():
    import asyncio

    from mcp_servers.servers.business_glossary import mcp

    async def _read():
        return await mcp.read_resource("glossary://database")

    contents = asyncio.run(_read())
    text = contents[0].content
    assert "analytics" in text
    assert "Descripcion:" in text


def test_business_glossary_list_metrics():
    import asyncio

    from mcp_servers.servers.business_glossary import mcp

    async def _read():
        return await mcp.read_resource("glossary://metrics")

    contents = asyncio.run(_read())
    text = contents[0].content
    assert "revenue" in text
    assert "average_order_value" in text


def test_business_glossary_get_metric_known():
    import asyncio

    from mcp_servers.servers.business_glossary import mcp

    async def _read():
        return await mcp.read_resource("glossary://metrics/revenue")

    contents = asyncio.run(_read())
    text = contents[0].content
    assert "revenue" in text
    assert "completed" in text


def test_business_glossary_get_metric_unknown():
    import asyncio

    from mcp_servers.servers.business_glossary import mcp

    async def _read():
        return await mcp.read_resource("glossary://metrics/nonexistent")

    contents = asyncio.run(_read())
    text = contents[0].content
    assert "no encontrada" in text


def test_business_glossary_list_tables():
    import asyncio

    from mcp_servers.servers.business_glossary import mcp

    async def _read():
        return await mcp.read_resource("glossary://tables")

    contents = asyncio.run(_read())
    text = contents[0].content
    assert "customers" in text
    assert "orders" in text


def test_business_glossary_get_table_known():
    import asyncio

    from mcp_servers.servers.business_glossary import mcp

    async def _read():
        return await mcp.read_resource("glossary://tables/customers")

    contents = asyncio.run(_read())
    text = contents[0].content
    assert "customers" in text
    assert "segment" in text


def test_business_glossary_get_table_unknown():
    import asyncio

    from mcp_servers.servers.business_glossary import mcp

    async def _read():
        return await mcp.read_resource("glossary://tables/nonexistent")

    contents = asyncio.run(_read())
    text = contents[0].content
    assert "no encontrada" in text


# ---- Analytics explorer (tools) ----


def test_analytics_explorer_server_builds():
    from mcp_servers.servers.analytics_explorer import create_server

    server = create_server()
    assert server.name == "analytics-explorer"


def test_analytics_explorer_tools_registered():
    import asyncio

    from mcp_servers.servers.analytics_explorer import create_server

    server = create_server()

    async def _get():
        return await server.list_tools()

    tools = asyncio.run(_get())
    names = {t.name for t in tools}

    assert names == {"list_tables", "describe_table", "sample_table"}


def test_analytics_explorer_list_tables_mocked():
    import asyncio

    from mcp_servers.servers.analytics_explorer import mcp

    fake_pool = _make_fake_pool(
        [("customers", "BASE TABLE"), ("orders", "BASE TABLE")]
    )

    async def _call():
        with patch(
            "mcp_servers.servers.analytics_explorer._pool", return_value=fake_pool
        ):
            return await mcp.call_tool("list_tables", {})

    content, _ = asyncio.run(_call())
    text = content[0].text
    assert "customers" in text
    assert "orders" in text
    assert "BASE TABLE" in text


def test_analytics_explorer_describe_table_mocked():
    import asyncio

    from mcp_servers.servers.analytics_explorer import mcp

    fake_pool = _make_fake_pool(
        [("id", "bigint", "NO"), ("name", "varchar", "YES")]
    )

    async def _call():
        with patch(
            "mcp_servers.servers.analytics_explorer._pool", return_value=fake_pool
        ):
            return await mcp.call_tool("describe_table", {"table": "customers"})

    content, _ = asyncio.run(_call())
    text = content[0].text
    assert "id" in text
    assert "bigint" in text
    assert "customers" in text


def test_analytics_explorer_describe_table_not_found():
    import asyncio

    from mcp_servers.servers.analytics_explorer import mcp

    fake_pool = _make_fake_pool([])

    async def _call():
        with patch(
            "mcp_servers.servers.analytics_explorer._pool", return_value=fake_pool
        ):
            return await mcp.call_tool("describe_table", {"table": "nonexistent"})

    content, _ = asyncio.run(_call())
    text = content[0].text
    assert "no encontrada" in text


# ---- Client ----


def test_mcp_client_builds_empty():
    from mcp_servers.client import build_mcp_client

    client = build_mcp_client()
    assert client.connections == {}


def test_mcp_client_builds_with_env(monkeypatch):
    from mcp_servers.client import build_mcp_client

    monkeypatch.setenv("MCP_GLOSSARY_URL", "http://glossary:8100/mcp")
    monkeypatch.setenv("MCP_EXPLORER_URL", "http://explorer:8101/mcp")

    client = build_mcp_client()

    assert "business-glossary" in client.connections
    assert "analytics-explorer" in client.connections
    assert client.connections["business-glossary"]["transport"] == "http"
    assert client.connections["business-glossary"]["url"] == "http://glossary:8100/mcp"