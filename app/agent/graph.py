from langgraph.graph import END, START, StateGraph

from app.agent.routing import route_after_execute, route_after_validate
from app.agent.state import AnalystState
from app.nodes.answer import generate_answer
from app.nodes.analyze import analyze_results
from app.nodes.execute_sql import execute_sql
from app.nodes.failure import failure
from app.nodes.fix_sql import fix_sql
from app.nodes.generate_sql import generate_sql
from app.nodes.schema import retrieve_schema
from app.nodes.validate_sql import validate_sql


def build_graph(checkpointer=None):

    graph = StateGraph(AnalystState)

    graph.add_node("retrieve_schema", retrieve_schema)
    graph.add_node("generate_sql", generate_sql)
    graph.add_node("validate_sql", validate_sql)
    graph.add_node("execute_sql", execute_sql)
    graph.add_node("fix_sql", fix_sql)
    graph.add_node("analyze_results", analyze_results)
    graph.add_node("generate_answer", generate_answer)
    graph.add_node("failure", failure)

    graph.add_edge(START, "retrieve_schema")
    graph.add_edge("retrieve_schema", "generate_sql")
    graph.add_edge("generate_sql", "validate_sql")

    graph.add_conditional_edges("validate_sql", route_after_validate)
    graph.add_conditional_edges("execute_sql", route_after_execute)

    graph.add_edge("fix_sql", "validate_sql")
    graph.add_edge("analyze_results", "generate_answer")
    graph.add_edge("generate_answer", END)
    graph.add_edge("failure", END)

    return graph.compile(checkpointer=checkpointer)


# Grafo sin persistencia para tests / uso directo.
agent_graph = build_graph()