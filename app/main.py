from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.agent.graph import build_graph
from app.api.routes import router
from app.infrastructure.postgres import checkpointer_lifespan, close_database, open_database
from mcp_servers.client import load_mcp_tools_safely


@asynccontextmanager
async def lifespan(app: FastAPI):
    await open_database()

    mcp_tools = await load_mcp_tools_safely()

    async with checkpointer_lifespan() as checkpointer:
        app.state.agent_graph = build_graph(
            checkpointer=checkpointer,
            mcp_tools=mcp_tools,
        )
        app.state.mcp_tools = mcp_tools
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