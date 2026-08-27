import time
from pathlib import Path

import yaml

from app.eval.metrics import (
    check_answer,
    check_filters,
    check_metric,
    compare_result,
    extract_tables,
)

DATASET_PATH = Path(__file__).resolve().parents[2] / "eval" / "dataset.yaml"


def load_dataset() -> list[dict]:
    with open(DATASET_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("cases", [])


async def evaluate_case(case: dict, graph, config: dict | None = None) -> dict:
    """Ejecuta el grafo para una pregunta y mide todas las dimensiones."""

    question = case["question"]
    expected_tables = set(case.get("expected_tables", []))
    expected_metric = case.get("expected_metric")
    expected_filters = case.get("expected_filters", {})
    expected_result = case.get("expected_result")
    expected_contains = case.get("expected_contains")

    state = {
        "question": question,
        "user_id": "eval",
        "thread_id": f"eval-{case.get('id', 'x')}",
        "retry_count": 0,
    }

    start = time.perf_counter()
    result = await graph.ainvoke(state, config=config or {})
    latency_ms = int((time.perf_counter() - start) * 1000)

    sql = result.get("generated_sql", "") or ""
    answer = result.get("answer", "") or ""
    query_result = result.get("query_result", []) or []

    tables = extract_tables(sql)
    tables_ok = expected_tables.issubset(tables) if expected_tables else True

    metric_ok = check_metric(sql, expected_metric)

    filters_ok, filters_missing = check_filters(sql, expected_filters)

    result_ok, result_actual = compare_result(query_result, expected_result)

    answer_ok = check_answer(answer, expected_contains)

    success = bool(result.get("success", False))

    return {
        "id": case.get("id"),
        "question": question,
        "latency_ms": latency_ms,
        "retries": int(result.get("retry_count", 0)),
        "success": success,
        "tables_ok": tables_ok,
        "metric_ok": metric_ok,
        "filters_ok": filters_ok,
        "filters_missing": filters_missing,
        "result_ok": result_ok,
        "result_actual": result_actual,
        "answer_ok": answer_ok,
        "sql": sql,
        "answer": answer,
    }


async def run_dataset(graph, config: dict | None = None) -> list[dict]:
    cases = load_dataset()
    return [await evaluate_case(c, graph, config) for c in cases]


PASS_DIMENSIONS = (
    "tables_ok",
    "metric_ok",
    "filters_ok",
    "result_ok",
    "answer_ok",
)


def summarize(results: list[dict]) -> dict:
    n = len(results)
    if n == 0:
        return {"n": 0}
    summary = {"n": n}
    for dim in PASS_DIMENSIONS:
        summary[dim] = sum(1 for r in results if r[dim])
    summary["latency_avg_ms"] = sum(r["latency_ms"] for r in results) // n
    summary["retries_avg"] = sum(r["retries"] for r in results) / n
    return summary


def format_report(results: list[dict]) -> str:
    summary = summarize(results)
    lines = ["Evaluacion del Data Analyst Agent", "=" * 40]
    for r in results:
        marks = "".join(
            "PASS" if r[d] else "FAIL"
            for d in PASS_DIMENSIONS
        )
        lines.append(
            f"[{r['id']:18}] lat={r['latency_ms']:5}ms "
            f"retries={r['retries']} {marks}"
        )
    lines.append("-" * 40)
    lines.append(
        f"Totales: sql_ok={summary['tables_ok']}/{summary['n']} "
        f"metric={summary['metric_ok']}/{summary['n']} "
        f"filters={summary['filters_ok']}/{summary['n']} "
        f"result={summary['result_ok']}/{summary['n']} "
        f"answer={summary['answer_ok']}/{summary['n']}"
    )
    lines.append(
        f"Latencia promedio: {summary['latency_avg_ms']}ms | "
        f"Retries promedio: {summary['retries_avg']:.1f}"
    )
    return "\n".join(lines)