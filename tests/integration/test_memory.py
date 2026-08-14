import os

import pytest


@pytest.mark.integration
@pytest.mark.agent
async def test_follow_up_persists_state(persistent_graph):

    thread_id = "test-memory-thread"
    config = {"configurable": {"thread_id": thread_id}}

    first = await persistent_graph.ainvoke(
        {
            "question": "¿Cuanto revenue hubo en julio?",
            "user_id": "t",
            "thread_id": thread_id,
            "retry_count": 0,
        },
        config=config,
    )

    assert first.get("answer"), "Primer turno sin respuesta"

    state = await persistent_graph.aget_state(config)

    assert state.values.get("question"), "El estado no se persistio"
    assert state.values.get("answer") == first["answer"]

    second = await persistent_graph.ainvoke(
        {
            "question": "¿Y solo los de Mexico?",
            "user_id": "t",
            "thread_id": thread_id,
            "retry_count": 0,
        },
        config=config,
    )

    assert second.get("answer"), "Follow-up sin respuesta"