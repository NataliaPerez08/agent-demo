from psycopg_pool import AsyncConnectionPool

from app.config import settings


analytics_pool = AsyncConnectionPool(
    conninfo=settings.analytics_database_url,
    open=False,
    min_size=1,
    max_size=10,
)

agent_pool = AsyncConnectionPool(
    conninfo=settings.agent_database_url,
    open=False,
    min_size=1,
    max_size=5,
)


async def open_database():
    await analytics_pool.open()
    await agent_pool.open()


async def close_database():
    await agent_pool.close()
    await analytics_pool.close()