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


class WidgetCreate(BaseModel):

    title: str
    question: str
    chart_type: str | None = None


class WidgetResponse(BaseModel):

    id: int
    dashboard_id: int
    title: str
    question: str
    chart_type: str | None = None
    position: int


class DashboardCreate(BaseModel):

    name: str
    description: str | None = None
    user_id: str | None = None


class DashboardResponse(BaseModel):

    id: int
    name: str
    description: str | None = None
    user_id: str
    widgets: list[WidgetResponse] = []


class DashboardRenderWidget(BaseModel):

    widget_id: int
    title: str
    question: str
    answer: str
    sql: str | None = None
    chart: ChartConfig | None = None
    rows: int = 0


class DashboardRenderResponse(BaseModel):

    dashboard_id: int
    name: str
    widgets: list[DashboardRenderWidget]