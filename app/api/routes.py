import uuid

from fastapi import APIRouter, HTTPException, Request

from app.api.schemas import ChatRequest, ChatResponse
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


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request):

    graph = http_request.app.state.agent_graph
    user_id = request.user_id or "anon"

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

    result = await graph.ainvoke(initial_state, config=config)

    # Refrescar TTL de sesion por actividad.
    await cache_expire(session_key, SESSION_TTL)

    return ChatResponse(
        thread_id=thread_id,
        answer=result.get("answer", ""),
        sql=result.get("generated_sql"),
    )