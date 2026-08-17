from app.agent.state import AnalystState


MAX_RETRIES = 2


MCP_KEYWORDS = {
    "web", "internet", "buscar en", "search", "archivo", "file",
    "document", "documento", "url", "link", "noticia", "weather",
    "clima", "email", "correo", "forecast", "pronostico",
    "externo", "external", "online",
}

SQL_KEYWORDS = {
    "revenue", "ventas", "cliente", "customer", "order", "pedido",
    "producto", "product", "sql", "query", "ingreso", "ticket",
    "pais", "country", "segmento", "segment", "julio", "junio",
    "comparar", "compare", "tendencia", "trend", "top", "mejor",
    "revenue", "promedio", "average", "total", "suma", "sum",
    "ordenes", "orders", "lineas",
}


def classify_question(state: AnalystState) -> dict:
    """Heuristica barata para clasificar la pregunta.

    Devuelve question_type="sql" (pipeline determinista) o "mcp"
    (loop reactivo con tools MCP). Default: "sql" porque el agente
    es primariamente un data analyst sobre la analytics DB.
    """

    question = (state.get("question") or "").lower()

    mcp_score = sum(1 for kw in MCP_KEYWORDS if kw in question)
    sql_score = sum(1 for kw in SQL_KEYWORDS if kw in question)

    if mcp_score > 0 and mcp_score > sql_score:
        return {"question_type": "mcp"}

    return {"question_type": "sql"}


def route_after_classify_factory(has_mcp: bool):
    """Factory de la funcion de routing tras classify.

    Si no hay tools MCP, siempre va al pipeline SQL (preserva
    compatibilidad con deployments sin MCP).
    """

    def route_after_classify(state: AnalystState) -> str:

        if has_mcp and state.get("question_type") == "mcp":
            return "agent_with_tools"

        return "generate_sql"

    return route_after_classify


def route_after_mcp_agent(state: AnalystState) -> str:
    """Routing tras el nodo agent_with_tools.

    Si el LLM pidio tool calls -> mcp_tools (ejecutar).
    Si no -> mcp_answer (extraer respuesta final).
    """

    messages = state.get("messages") or []
    last = messages[-1] if messages else None

    if last and getattr(last, "tool_calls", None):
        return "mcp_tools"

    return "mcp_answer"


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