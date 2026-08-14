from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.infrastructure.postgres import open_database, close_database

@asynccontextmanager
async def lifespan(app: FastAPI):
    await open_database()
    yield
    await close_database()

app = FastAPI(
    title="Data Analyst Agent",
    version="0.1.0",
    lifespan=lifespan,
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}