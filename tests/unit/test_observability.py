import asyncio

from app.infrastructure.observability import (
    Observation,
    format_observation,
    get_observation,
    reset_observation,
    set_observation,
    timed,
)


def test_observation_phases_and_tokens():

    obs = Observation(request_id="req-1")

    obs.record_phase("schema", 20)
    obs.record_phase("generate_sql", 820)
    obs.record_phase("database", 34)

    obs.add_tokens("analyst-smart", prompt=1200, completion=80)
    obs.add_tokens("analyst-smart", prompt=900, completion=60)

    assert obs.phases == {"schema": 20, "generate_sql": 820, "database": 34}
    assert obs.prompt_tokens == 2100
    assert obs.completion_tokens == 140
    assert obs.total_tokens == 2240
    assert obs.models == {"analyst-smart"}

    expected_cost = (
        2100 * 1.50 / 1_000_000 + 140 * 6.00 / 1_000_000
    )
    assert abs(obs.estimated_cost - expected_cost) < 1e-12


def test_format_observation_contains_fields():

    obs = Observation(request_id="req-2")
    obs.record_phase("schema", 10)
    obs.record_phase("execute_sql", 50)
    obs.add_tokens("analyst-fast", prompt=100, completion=10)

    report = format_observation(obs)

    assert "request: req-2" in report
    assert "schema=10ms" in report
    assert "execute_sql=50ms" in report
    assert "total=60ms" in report
    assert "tokens in=100 out=10" in report
    assert "cost=" in report


async def _timed_node(state):

    await asyncio.sleep(0)

    return {"x": 1}


def test_timed_wrapper_records_phase_into_contextvar():

    obs = Observation(request_id="req-3")
    token = set_observation(obs)

    try:

        wrapped = timed("generate_sql")(_timed_node)

        result = asyncio.run(wrapped({"q": "x"}))

    finally:

        reset_observation(token)

    assert result == {"x": 1}
    assert "generate_sql" in obs.phases
    assert obs.phases["generate_sql"] >= 0


def test_get_observation_returns_none_by_default():

    assert get_observation() is None