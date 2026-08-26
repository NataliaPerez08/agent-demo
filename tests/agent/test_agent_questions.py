import pytest

QUESTIONS = [
    "¿Cuanto revenue hubo en julio?",
    "¿Cuales fueron los 5 clientes con mas revenue?",
    "¿Que pais genero mas revenue?",
    "Compara junio contra julio.",
    "¿Que productos vendieron mas unidades?",
    "¿Cual fue el ticket promedio?",
]


@pytest.mark.agent
@pytest.mark.parametrize("question", QUESTIONS)
async def test_agent_answers(question, full_stack):
    from app.agent.graph import agent_graph

    result = await agent_graph.ainvoke(
        {
            "question": question,
            "user_id": "test",
            "thread_id": "test-thread",
            "retry_count": 0,
        }
    )

    assert result.get("answer"), f"Sin respuesta para: {question}"