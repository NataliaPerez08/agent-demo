import json
import os
import uuid

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    DashboardCreate,
    DashboardRenderResponse,
    DashboardRenderWidget,
    DashboardResponse,
    ModelInfo,
    ModelsResponse,
    WidgetCreate,
    WidgetResponse,
)
from app.config import settings
from app.infrastructure.audit import log_query
from app.infrastructure.dashboards import (
    add_widget,
    create_dashboard,
    delete_dashboard,
    delete_widget,
    get_dashboard,
    list_dashboards,
)
from app.infrastructure.observability import (
    Observation,
    log_observation,
    reset_observation,
    set_observation,
)
from app.infrastructure.redis import (
    cache_expire,
    cache_get,
    cache_incr_with_ttl,
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

DEFAULT_MODEL = settings.analyst_model

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


# ---- /models ----


@router.get("/models", response_model=ModelsResponse)
async def list_models():

    maas_available = bool(settings.maas_api_key)

    ollama_available = False
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{OLLAMA_HOST}/api/tags")
            ollama_available = resp.status_code == 200
    except Exception:
        pass

    models = [
        ModelInfo(
            name="analyst-smart",
            label="Smart (OpenAI via MAAS)",
            available=maas_available,
        ),
        ModelInfo(
            name="analyst-fast",
            label="Fast (OpenAI via MAAS)",
            available=maas_available,
        ),
        ModelInfo(
            name="analyst-local",
            label="Local (Ollama qwen2.5:7b)",
            available=ollama_available,
        ),
        ModelInfo(
            name="analyst-local-fast",
            label="Local Fast (Ollama qwen2.5:1.5b)",
            available=ollama_available,
        ),
    ]

    return ModelsResponse(models=models)


# ---- /chat ----


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request):

    graph = http_request.app.state.agent_graph
    user_id = request.user_id or "anon"
    request_id = str(uuid.uuid4())

    count = await cache_incr_with_ttl(f"rl:{user_id}", RATE_LIMIT_WINDOW)
    if count > RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Demasiadas solicitudes.")

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
        "model": request.model or DEFAULT_MODEL,
        "retry_count": 0,
    }

    obs = Observation(request_id=request_id)
    token = set_observation(obs)

    try:

        result = await graph.ainvoke(initial_state, config=config)

    finally:

        reset_observation(token)

    await cache_expire(session_key, SESSION_TTL)

    query_result = result.get("query_result", []) or []

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
            "model": request.model or DEFAULT_MODEL,
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
        rows=query_result[:50] if query_result else None,
        row_count=len(query_result) if query_result else 0,
    )


# ---- /export ----


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
# ---- /dashboards ----
@router.post("/dashboards", response_model=DashboardResponse)
async def create_dashboard_endpoint(request: DashboardCreate):

    user_id = request.user_id or "anon"

    dashboard = await create_dashboard(
        name=request.name,
        description=request.description,
        user_id=user_id,
    )

    if not dashboard:
        raise HTTPException(status_code=500, detail="No se pudo crear el dashboard.")

    return DashboardResponse(
        id=dashboard["id"],
        name=dashboard["name"],
        description=dashboard.get("description"),
        user_id=dashboard["user_id"],
        widgets=[],
    )


@router.get("/dashboards", response_model=list[DashboardResponse])
async def list_dashboards_endpoint(user_id: str = Query("anon")):

    dashboards = await list_dashboards(user_id)

    return [
        DashboardResponse(
            id=d["id"],
            name=d["name"],
            description=d.get("description"),
            user_id=d["user_id"],
            widgets=[],
        )
        for d in dashboards
    ]


@router.get("/dashboards/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard_endpoint(dashboard_id: int):

    dashboard = await get_dashboard(dashboard_id)

    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard no encontrado.")

    widgets = [
        WidgetResponse(
            id=w["id"],
            dashboard_id=w["dashboard_id"],
            title=w["title"],
            question=w["question"],
            chart_type=w.get("chart_type"),
            position=w["position"],
        )
        for w in dashboard.get("widgets", [])
    ]

    return DashboardResponse(
        id=dashboard["id"],
        name=dashboard["name"],
        description=dashboard.get("description"),
        user_id=dashboard["user_id"],
        widgets=widgets,
    )


@router.delete("/dashboards/{dashboard_id}")
async def delete_dashboard_endpoint(dashboard_id: int):

    deleted = await delete_dashboard(dashboard_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Dashboard no encontrado.")

    return {"deleted": True}


@router.post("/dashboards/{dashboard_id}/widgets", response_model=WidgetResponse)
async def add_widget_endpoint(dashboard_id: int, request: WidgetCreate):

    dashboard = await get_dashboard(dashboard_id)

    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard no encontrado.")

    position = len(dashboard.get("widgets", []))

    widget = await add_widget(
        dashboard_id=dashboard_id,
        title=request.title,
        question=request.question,
        chart_type=request.chart_type,
        position=position,
    )

    if not widget:
        raise HTTPException(status_code=500, detail="No se pudo crear el widget.")

    return WidgetResponse(
        id=widget["id"],
        dashboard_id=widget["dashboard_id"],
        title=widget["title"],
        question=widget["question"],
        chart_type=widget.get("chart_type"),
        position=widget["position"],
    )


@router.delete("/dashboards/{dashboard_id}/widgets/{widget_id}")
async def delete_widget_endpoint(dashboard_id: int, widget_id: int):

    deleted = await delete_widget(dashboard_id, widget_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Widget no encontrado.")

    return {"deleted": True}


@router.get("/dashboards/{dashboard_id}/render", response_model=DashboardRenderResponse)
async def render_dashboard_endpoint(dashboard_id: int, http_request: Request):

    dashboard = await get_dashboard(dashboard_id)

    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard no encontrado.")

    graph = http_request.app.state.agent_graph

    render_widgets = []

    for widget in dashboard.get("widgets", []):

        widget_state = {
            "question": widget["question"],
            "user_id": f"dashboard-{dashboard_id}",
            "thread_id": f"widget-{widget['id']}",
            "retry_count": 0,
        }

        try:

            result = await graph.ainvoke(widget_state)

        except Exception as exc:

            render_widgets.append(
                DashboardRenderWidget(
                    widget_id=widget["id"],
                    title=widget["title"],
                    question=widget["question"],
                    answer=f"Error: {exc}",
                    sql=None,
                    chart=None,
                    rows=0,
                )
            )
            continue

        query_result = result.get("query_result", []) or []

        chart = suggest_chart(query_result, widget["question"])

        render_widgets.append(
            DashboardRenderWidget(
                widget_id=widget["id"],
                title=widget["title"],
                question=widget["question"],
                answer=result.get("answer", ""),
                sql=result.get("generated_sql"),
                chart=chart,
                rows=len(query_result),
            )
        )

    return DashboardRenderResponse(
        dashboard_id=dashboard["id"],
        name=dashboard["name"],
        widgets=render_widgets,
    )