import uuid

from fastapi import APIRouter, HTTPException, Request

from app.api.schemas import ChatRequest, ChatResponse
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


router = APIRouter()

SESSION_PREFIX = "session:"
SESSION_TTL = 86400

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
            "row_count": len(result.get("query_result", [])),
            "model": DEFAULT_MODEL,
            "retry_count": int(result.get("retry_count", 0)),
        }
    )

    log_observation(obs)

    return ChatResponse(
        thread_id=thread_id,
        answer=result.get("answer", ""),
        sql=result.get("generated_sql"),
    )