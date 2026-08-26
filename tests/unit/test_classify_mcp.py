"""Tests del clasificador de preguntas y la bifurcacion SQL | MCP."""

import pytest

from app.agent.routing import (
    classify_question,
    route_after_classify_factory,
    route_after_mcp_agent,
)

# ---- classify_question ----


@pytest.mark.parametrize(
    "question, expected",
    [
        ("¿Cuanto revenue hubo en julio?", "sql"),
        ("¿Cuales fueron los 5 clientes con mas revenue?", "sql"),
        ("¿Que pais genero mas revenue?", "sql"),
        ("Compara junio contra julio.", "sql"),
        ("¿Que productos vendieron mas unidades?", "sql"),
        ("¿Cual fue el ticket promedio?", "sql"),
        ("Busca en la web noticias sobre IA.", "mcp"),
        ("Lee el archivo README.md", "mcp"),
        ("¿Que clima hace en Mexico?", "mcp"),
        ("Busca en internet el forecast de ventas", "mcp"),
        ("", "sql"),
        ("Hola", "sql"),
    ],
)
def test_classify_question(question, expected):
    result = classify_question({"question": question})
    assert result["question_type"] == expected


def test_classify_sql_wins_over_mcp_when_both_present():
    result = classify_question(
        {"question": "Busca el revenue del archivo de ventas de julio"}
    )
    assert result["question_type"] == "sql"


# ---- route_after_classify ----


def test_route_after_classify_sql_no_mcp():
    route = route_after_classify_factory(has_mcp=False)
    assert route({"question_type": "sql"}) == "generate_sql"


def test_route_after_classify_mcp_ignored_without_tools():
    route = route_after_classify_factory(has_mcp=False)
    assert route({"question_type": "mcp"}) == "generate_sql"


def test_route_after_classify_sql_with_mcp():
    route = route_after_classify_factory(has_mcp=True)
    assert route({"question_type": "sql"}) == "generate_sql"


def test_route_after_classify_mcp_with_tools():
    route = route_after_classify_factory(has_mcp=True)
    assert route({"question_type": "mcp"}) == "agent_with_tools"


# ---- route_after_mcp_agent ----


class _FakeMessage:
    def __init__(self, tool_calls=None, content=""):
        self.tool_calls = tool_calls
        self.content = content


def test_route_after_mcp_agent_with_tool_calls():
    state = {"messages": [_FakeMessage(tool_calls=[{"name": "search"}])]}
    assert route_after_mcp_agent(state) == "mcp_tools"


def test_route_after_mcp_agent_without_tool_calls():
    state = {"messages": [_FakeMessage(tool_calls=None, content="respuesta")]}
    assert route_after_mcp_agent(state) == "mcp_answer"


def test_route_after_mcp_agent_empty_messages():
    state = {"messages": []}
    assert route_after_mcp_agent(state) == "mcp_answer"


def test_route_after_mcp_agent_no_messages_key():
    state = {}
    assert route_after_mcp_agent(state) == "mcp_answer"