import pytest


@pytest.mark.integration
@pytest.mark.agent
async def test_graph_end_to_end(full_stack):
    from app.agent.graph import agent_graph

    result = await agent_graph.ainvoke(
        {
            "question": "¿Cuanto revenue hubo en julio?",
            "user_id": "test",
            "thread_id": "test-thread",
            "retry_count": 0,
        }
    )

    assert result.get("answer"), "El agente no devolvio respuesta"
    assert result.get("generated_sql"), "El agente no devolvio SQL"