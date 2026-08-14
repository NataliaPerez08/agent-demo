from app.agent.state import AnalystState


MAX_RETRIES = 2


def route_after_validate(state: AnalystState) -> str:

    if state.get("sql_valid"):

        return "execute_sql"

    error = state.get("validation_error") or ""

    if "no puede responderse" in error:

        return "failure"

    if state.get("retry_count", 0) < MAX_RETRIES:

        return "fix_sql"

    return "failure"


def route_after_execute(state: AnalystState) -> str:

    if state.get("execution_error"):

        if state.get("retry_count", 0) < MAX_RETRIES:

            return "fix_sql"

        return "failure"

    return "analyze_results"