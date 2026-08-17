from pydantic import BaseModel


class ChatRequest(BaseModel):

    question: str
    user_id: str | None = None


class ChartConfig(BaseModel):

    type: str
    title: str
    x: str | None = None
    y: str | None = None
    series: list[str] | None = None
    columns: list[str] | None = None


class ChatResponse(BaseModel):

    thread_id: str
    answer: str
    sql: str | None = None
    chart: ChartConfig | None = None


class ExportResponse(BaseModel):

    rows: int
    format: str