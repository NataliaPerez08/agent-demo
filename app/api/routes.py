import uuid

from fastapi import APIRouter

from app.agent.graph import agent_graph
from app.api.schemas import ChatRequest, ChatResponse


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):

    thread_id = str(uuid.uuid4())

    initial_state = {
        "question": request.question,
        "user_id": request.user_id or "anon",
        "thread_id": thread_id,
        "retry_count": 0,
    }

    result = await agent_graph.ainvoke(initial_state)

    return ChatResponse(
        thread_id=thread_id,
        answer=result.get("answer", ""),
        sql=result.get("generated_sql"),
    )