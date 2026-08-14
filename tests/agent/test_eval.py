import pytest


@pytest.mark.agent
async def test_eval_runs_and_reports(full_stack):
    from app.eval.evaluator import format_report, run_dataset, summarize

    from app.agent.graph import build_graph

    # Sin checkpointer: evaluacion fresh por caso (thread_id unico igual).
    graph = build_graph()

    results = await run_dataset(graph)

    assert len(results) > 0, "Dataset vacio"

    for r in results:
        assert r["sql"], f"Sin SQL para: {r['question']}"
        assert r["answer"], f"Sin respuesta para: {r['question']}"
        assert "latency_ms" in r
        assert "retries" in r

    summary = summarize(results)
    assert summary["n"] == len(results)

    report = format_report(results)
    assert "Evaluacion" in report
    print("\n" + report)


@pytest.mark.agent
async def test_eval_simple_revenue_matches(full_stack):
    """El caso mas simple debe acertar resultado y tablas."""
    from app.eval.evaluator import evaluate_case, load_dataset

    from app.agent.graph import build_graph

    graph = build_graph()

    cases = {c["id"]: c for c in load_dataset()}
    case = cases["revenue_julio"]

    r = await evaluate_case(case, graph)

    assert r["tables_ok"], f"Tablas incorrectas: {r['sql']}"
    assert r["result_ok"], (
        f"Resultado incorrecto: esperado {case['expected_result']}, "
        f"actual {r['result_actual']}"
    )