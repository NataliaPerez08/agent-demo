from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent.mcp_tools import make_agent_with_tools, mcp_answer
from app.agent.routing import (
    classify_question,
    route_after_classify_factory,
    route_after_execute,
    route_after_mcp_agent,
    route_after_validate,
)
from app.agent.state import AnalystState
from app.infrastructure.observability import timed
from app.nodes.answer import generate_answer
from app.nodes.analyze import analyze_results
from app.nodes.execute_sql import execute_sql
from app.nodes.failure import failure
from app.nodes.fix_sql import fix_sql
from app.nodes.generate_sql import generate_sql
from app.nodes.schema import retrieve_schema
from app.nodes.validate_sql import validate_sql


def build_graph(checkpointer=None, mcp_tools=None):
    """Construye el grafo del agente.

    - mcp_tools=None o []: grafo pipeline-only (preserva compatibilidad).
    - mcp_tools=[...]: grafo hibrido con bifurcacion classify -> SQL | MCP.
    """

    has_mcp = bool(mcp_tools)

    route_after_classify = route_after_classify_factory(has_mcp)

    graph = StateGraph(AnalystState)

    graph.add_node("retrieve_schema", timed("schema")(retrieve_schema))
    graph.add_node("classify", classify_question)
    graph.add_node("generate_sql", timed("generate_sql")(generate_sql))
    graph.add_node("validate_sql", timed("validate_sql")(validate_sql))
    graph.add_node("execute_sql", timed("execute_sql")(execute_sql))
    graph.add_node("fix_sql", timed("fix_sql")(fix_sql))
    graph.add_node("analyze_results", timed("analyze")(analyze_results))
    graph.add_node("generate_answer", timed("answer")(generate_answer))
    graph.add_node("failure", failure)

    if has_mcp:
        graph.add_node(
            "agent_with_tools",
            timed("mcp_agent")(make_agent_with_tools(mcp_tools)),
        )
        graph.add_node("mcp_tools", ToolNode(mcp_tools))
        graph.add_node("mcp_answer", timed("mcp_answer")(mcp_answer))

    graph.add_edge(START, "retrieve_schema")
    graph.add_edge("retrieve_schema", "classify")

    graph.add_conditional_edges("classify", route_after_classify)

    graph.add_edge("generate_sql", "validate_sql")

    graph.add_conditional_edges("validate_sql", route_after_validate)
    graph.add_conditional_edges("execute_sql", route_after_execute)

    graph.add_edge("fix_sql", "validate_sql")
    graph.add_edge("analyze_results", "generate_answer")
    graph.add_edge("generate_answer", END)
    graph.add_edge("failure", END)

    if has_mcp:
        graph.add_conditional_edges("agent_with_tools", route_after_mcp_agent)
        graph.add_edge("mcp_tools", "agent_with_tools")
        graph.add_edge("mcp_answer", END)

    return graph.compile(checkpointer=checkpointer)


# Grafo sin persistencia ni MCP para tests / uso directo.
agent_graph = build_graph()