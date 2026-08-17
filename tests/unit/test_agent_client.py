"""Tests del cliente HTTP del chatbot (AgentClient).

Probado con httpx.AsyncClient mockeado (sin red ni API real).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_chat_success():
    from chatbot.agent_client import AgentClient

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.raise_for_status = MagicMock()
    fake_response.json = MagicMock(
        return_value={
            "thread_id": "t-123",
            "answer": "El revenue fue 52500.",
            "sql": "SELECT SUM(total) FROM orders",
            "chart": {"type": "bar", "title": "Revenue"},
        }
    )

    fake_client = AsyncMock()
    fake_client.post = AsyncMock(return_value=fake_response)

    with patch("chatbot.agent_client.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=fake_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        client = AgentClient("http://localhost:8000")
        result = await client.chat("¿Cuanto revenue?")

    assert result["thread_id"] == "t-123"
    assert "52500" in result["answer"]
    assert result["sql"] == "SELECT SUM(total) FROM orders"


@pytest.mark.asyncio
async def test_health_ok():
    from chatbot.agent_client import AgentClient

    fake_response = MagicMock()
    fake_response.status_code = 200

    fake_client = AsyncMock()
    fake_client.get = AsyncMock(return_value=fake_response)

    with patch("chatbot.agent_client.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=fake_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        client = AgentClient("http://localhost:8000")
        ok = await client.health()

    assert ok is True


@pytest.mark.asyncio
async def test_health_fail():
    from chatbot.agent_client import AgentClient

    with patch("chatbot.agent_client.httpx.AsyncClient") as mock_cls:
        mock_cls.side_effect = ConnectionError("no server")

        client = AgentClient("http://localhost:8000")
        ok = await client.health()

    assert ok is False


@pytest.mark.asyncio
async def test_export_csv():
    from chatbot.agent_client import AgentClient

    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.content = b"name,revenue\nAcme,6000\n"

    fake_client = AsyncMock()
    fake_client.get = AsyncMock(return_value=fake_response)

    with patch("chatbot.agent_client.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=fake_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        client = AgentClient("http://localhost:8000")
        data = await client.export_csv("t-123")

    assert b"name,revenue" in data
    assert b"Acme,6000" in data


def test_base_url_strips_trailing_slash():
    from chatbot.agent_client import AgentClient

    client = AgentClient("http://localhost:8000/")
    assert client.base_url == "http://localhost:8000"