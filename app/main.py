from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.agent.graph import build_graph
from app.api.routes import router
from app.infrastructure.postgres import checkpointer_lifespan, close_database, open_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    await open_database()
    async with checkpointer_lifespan() as checkpointer:
        app.state.agent_graph = build_graph(checkpointer)
        yield
    await close_database()


app = FastAPI(
    title="Data Analyst Agent",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}