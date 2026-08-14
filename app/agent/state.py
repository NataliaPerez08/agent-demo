from typing import Any, TypedDict


class AnalystState(TypedDict, total=False):

    question: str

    thread_id: str
    user_id: str

    schema_context: str

    generated_sql: str

    sql_valid: bool
    validation_error: str | None

    query_result: list[dict[str, Any]]

    analysis: str
    answer: str

    retry_count: int