"""Tests de dashboards: CRUD y render con DB mockeada (sin infra)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class _FakeAsyncCM:
    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, *a):
        return None


def _fake_pool(fetchone_return=None, fetchall_return=None):
    fake_cursor = MagicMock()
    fake_cursor.fetchone = AsyncMock(return_value=fetchone_return)
    fake_cursor.fetchall = AsyncMock(return_value=fetchall_return or [])
    fake_cursor.execute = AsyncMock()

    fake_conn = MagicMock()
    fake_conn.cursor.return_value = _FakeAsyncCM(fake_cursor)

    fake_pool = MagicMock()
    fake_pool.connection.return_value = _FakeAsyncCM(fake_conn)

    return fake_pool


# ---- Dashboard CRUD ----


@pytest.mark.asyncio
async def test_create_dashboard():
    from app.infrastructure.dashboards import create_dashboard

    fake = _fake_pool(
        fetchone_return={"id": 1, "name": "Ventas", "description": None, "user_id": "anon"}
    )

    with patch("app.infrastructure.dashboards.agent_pool", fake):
        result = await create_dashboard("Ventas", None, "anon")

    assert result is not None
    assert result["id"] == 1
    assert result["name"] == "Ventas"


@pytest.mark.asyncio
async def test_create_dashboard_error():
    from app.infrastructure.dashboards import create_dashboard

    fake = MagicMock()
    fake.connection.side_effect = RuntimeError("DB down")

    with patch("app.infrastructure.dashboards.agent_pool", fake):
        result = await create_dashboard("x", None, "anon")

    assert result is None


@pytest.mark.asyncio
async def test_get_dashboard_with_widgets():
    from app.infrastructure.dashboards import get_dashboard

    dashboard_row = {"id": 1, "name": "Ventas", "description": "Desc", "user_id": "anon"}
    widget_rows = [
        {"id": 10, "dashboard_id": 1, "title": "Revenue", "question": "¿Revenue?", "chart_type": "bar", "position": 0},
        {"id": 11, "dashboard_id": 1, "title": "Top clientes", "question": "¿Top 5?", "chart_type": None, "position": 1},
    ]

    fetchone_returns = [dashboard_row, None]
    fetchone_call = [0]

    async def _fetchone():
        idx = min(fetchone_call[0], len(fetchone_returns) - 1)
        val = fetchone_returns[idx]
        fetchone_call[0] += 1
        return val

    fake_cursor = MagicMock()
    fake_cursor.fetchone = _fetchone
    fake_cursor.fetchall = AsyncMock(return_value=widget_rows)
    fake_cursor.execute = AsyncMock()

    fake_conn = MagicMock()
    fake_conn.cursor.return_value = _FakeAsyncCM(fake_cursor)

    fake_pool = MagicMock()
    fake_pool.connection.return_value = _FakeAsyncCM(fake_conn)

    with patch("app.infrastructure.dashboards.agent_pool", fake_pool):
        result = await get_dashboard(1)

    assert result is not None
    assert result["id"] == 1
    assert len(result["widgets"]) == 2
    assert result["widgets"][0]["title"] == "Revenue"


@pytest.mark.asyncio
async def test_get_dashboard_not_found():
    from app.infrastructure.dashboards import get_dashboard

    fake = _fake_pool(fetchone_return=None)

    with patch("app.infrastructure.dashboards.agent_pool", fake):
        result = await get_dashboard(999)

    assert result is None


@pytest.mark.asyncio
async def test_list_dashboards():
    from app.infrastructure.dashboards import list_dashboards

    rows = [
        {"id": 1, "name": "Ventas", "description": None, "user_id": "anon"},
        {"id": 2, "name": "Clientes", "description": "Top", "user_id": "anon"},
    ]

    fake = _fake_pool(fetchall_return=rows)

    with patch("app.infrastructure.dashboards.agent_pool", fake):
        result = await list_dashboards("anon")

    assert len(result) == 2
    assert result[0]["name"] == "Ventas"


@pytest.mark.asyncio
async def test_delete_dashboard_success():
    from app.infrastructure.dashboards import delete_dashboard

    fake_cursor = MagicMock()
    fake_cursor.fetchone = AsyncMock(return_value=(1,))
    fake_cursor.execute = AsyncMock()

    fake_conn = MagicMock()
    fake_conn.cursor.return_value = _FakeAsyncCM(fake_cursor)

    fake_pool = MagicMock()
    fake_pool.connection.return_value = _FakeAsyncCM(fake_conn)

    with patch("app.infrastructure.dashboards.agent_pool", fake_pool):
        result = await delete_dashboard(1)

    assert result is True


@pytest.mark.asyncio
async def test_delete_dashboard_not_found():
    from app.infrastructure.dashboards import delete_dashboard

    fake_cursor = MagicMock()
    fake_cursor.fetchone = AsyncMock(return_value=None)
    fake_cursor.execute = AsyncMock()

    fake_conn = MagicMock()
    fake_conn.cursor.return_value = _FakeAsyncCM(fake_cursor)

    fake_pool = MagicMock()
    fake_pool.connection.return_value = _FakeAsyncCM(fake_conn)

    with patch("app.infrastructure.dashboards.agent_pool", fake_pool):
        result = await delete_dashboard(999)

    assert result is False


# ---- Widget CRUD ----


@pytest.mark.asyncio
async def test_add_widget():
    from app.infrastructure.dashboards import add_widget

    fake = _fake_pool(
        fetchone_return={
            "id": 10,
            "dashboard_id": 1,
            "title": "Revenue",
            "question": "¿Revenue?",
            "chart_type": "bar",
            "position": 0,
        }
    )

    with patch("app.infrastructure.dashboards.agent_pool", fake):
        result = await add_widget(1, "Revenue", "¿Revenue?", "bar", 0)

    assert result is not None
    assert result["id"] == 10
    assert result["title"] == "Revenue"


@pytest.mark.asyncio
async def test_delete_widget_success():
    from app.infrastructure.dashboards import delete_widget

    fake_cursor = MagicMock()
    fake_cursor.fetchone = AsyncMock(return_value=(10,))
    fake_cursor.execute = AsyncMock()

    fake_conn = MagicMock()
    fake_conn.cursor.return_value = _FakeAsyncCM(fake_cursor)

    fake_pool = MagicMock()
    fake_pool.connection.return_value = _FakeAsyncCM(fake_conn)

    with patch("app.infrastructure.dashboards.agent_pool", fake_pool):
        result = await delete_widget(1, 10)

    assert result is True


@pytest.mark.asyncio
async def test_delete_widget_not_found():
    from app.infrastructure.dashboards import delete_widget

    fake_cursor = MagicMock()
    fake_cursor.fetchone = AsyncMock(return_value=None)
    fake_cursor.execute = AsyncMock()

    fake_conn = MagicMock()
    fake_conn.cursor.return_value = _FakeAsyncCM(fake_cursor)

    fake_pool = MagicMock()
    fake_pool.connection.return_value = _FakeAsyncCM(fake_conn)

    with patch("app.infrastructure.dashboards.agent_pool", fake_pool):
        result = await delete_widget(1, 999)

    assert result is False