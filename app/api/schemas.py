from pydantic import BaseModel


class ChatRequest(BaseModel):

    question: str
    user_id: str | None = None


class ChatResponse(BaseModel):

    thread_id: str
    answer: str
    sql: str | None = None