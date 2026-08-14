import json
import uuid

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.api.schemas import ChatRequest, ChatResponse, ExportResponse
from app.infrastructure.audit import log_query
from app.infrastructure.observability import (
    Observation,
    log_observation,
    reset_observation,
    set_observation,
)
from app.infrastructure.redis import (
    cache_expire,
    cache_incr_with_ttl,
    cache_get,
    cache_set,
)
from app.services.charts import suggest_chart
from app.services.export import rows_to_csv, rows_to_excel


router = APIRouter()

SESSION_PREFIX = "session:"
SESSION_TTL = 86400

RESULT_PREFIX = "result:"
RESULT_TTL = 3600

RATE_LIMIT_MAX = 30
RATE_LIMIT_WINDOW = 60

DEFAULT_MODEL = "analyst-smart"


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request):

    graph = http_request.app.state.agent_graph
    user_id = request.user_id or "anon"
    request_id = str(uuid.uuid4())

    # Rate limit por usuario (fail-open si Redis no responde).
    count = await cache_incr_with_ttl(f"rl:{user_id}", RATE_LIMIT_WINDOW)
    if count > RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Demasiadas solicitudes.")

    # Recuperar o crear thread_id: misma sesion de usuario -> mismo thread
    # (habilita follow-ups conversacionales).
    session_key = f"{SESSION_PREFIX}{user_id}"
    thread_id = await cache_get(session_key)
    if not thread_id:
        thread_id = str(uuid.uuid4())
        await cache_set(session_key, thread_id, SESSION_TTL)

    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "question": request.question,
        "user_id": user_id,
        "thread_id": thread_id,
        "retry_count": 0,
    }

    # Observabilidad: contextvar aislada por request.
    obs = Observation(request_id=request_id)
    token = set_observation(obs)

    try:

        result = await graph.ainvoke(initial_state, config=config)

    finally:

        reset_observation(token)

    # Refrescar TTL de sesion por actividad.
    await cache_expire(session_key, SESSION_TTL)

    query_result = result.get("query_result", []) or []

    # Guardar ultimo resultado del thread para export reutilizable.
    try:
        await cache_set(
            f"{RESULT_PREFIX}{thread_id}",
            json.dumps(query_result, default=str),
            RESULT_TTL,
        )
    except Exception:
        pass

    await log_query(
        {
            "request_id": request_id,
            "user_id": user_id,
            "thread_id": thread_id,
            "question": request.question,
            "generated_sql": result.get("generated_sql"),
            "successful": bool(result.get("success", False)),
            "error": result.get("execution_error") or result.get("validation_error"),
            "execution_ms": int(result.get("execution_ms", 0)),
            "row_count": len(query_result),
            "model": DEFAULT_MODEL,
            "retry_count": int(result.get("retry_count", 0)),
        }
    )

    log_observation(obs)

    chart = suggest_chart(query_result, request.question)

    return ChatResponse(
        thread_id=thread_id,
        answer=result.get("answer", ""),
        sql=result.get("generated_sql"),
        chart=chart,
    )


@router.get("/export")
async def export(
    http_request: Request,
    thread_id: str = Query(..., description="thread_id del /chat"),
    fmt: str = Query("csv", pattern="^(csv|xlsx)$"),
):

    raw = await cache_get(f"{RESULT_PREFIX}{thread_id}")

    if not raw:
        raise HTTPException(
            status_code=404,
            detail="No hay resultados recientes para este thread_id.",
        )

    rows = json.loads(raw)

    if not rows:
        raise HTTPException(status_code=404, detail="La consulta no devolvio filas.")

    if fmt == "csv":
        content = rows_to_csv(rows)
        return StreamingResponse(
            iter([content]),
            media_type="text/csv",
            headers={
                "Content-Disposition": (
                    f"attachment; filename=results_{thread_id}.csv"
                )
            },
        )

    data = rows_to_excel(rows)
    return StreamingResponse(
        iter([data]),
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                f"attachment; filename=results_{thread_id}.xlsx"
            )
        },
    )