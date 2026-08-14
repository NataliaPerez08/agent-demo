import os

# Defaults apuntan a los puertos publicados en host por docker-compose.
# Solo se aplican si la variable no esta definida previamente, asi que
# un .env o un entorno CI pueden sobreescribirlos.
os.environ.setdefault("LITELLM_BASE_URL", "http://localhost:4000/v1")
os.environ.setdefault("LITELLM_MASTER_KEY", "sk-local-secret")
os.environ.setdefault("AGENT_DATABASE_URL", "postgresql://agent:agent@localhost:5432/agent")
os.environ.setdefault("ANALYTICS_DATABASE_URL", "postgresql://analyst_agent:analyst@localhost:5433/analytics")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import pytest


async def _can_connect() -> bool:
    from app.infrastructure.postgres import analytics_pool

    try:
        await analytics_pool.open()
        async with analytics_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                await cur.fetchone()
        return True
    except Exception:
        return False
    finally:
        try:
            await analytics_pool.close()
        except Exception:
            pass


def _llm_ready() -> bool:
    key = os.environ.get("OPENAI_API_KEY", "")
    return bool(key) and key != "TU_API_KEY"


@pytest.fixture
async def analytics_pool_ready():
    """Abre el pool de analytics y hace skip si la DB no esta disponible."""
    if not await _can_connect():
        pytest.skip("analytics DB unavailable (levantar docker compose)")

    from app.infrastructure.postgres import analytics_pool

    await analytics_pool.open()
    try:
        yield analytics_pool
    finally:
        await analytics_pool.close()


@pytest.fixture
async def full_stack():
    """Requiere LLM + DB. Gated por RUN_AGENT=1 para evitar coste accidental."""
    if os.environ.get("RUN_AGENT") != "1":
        pytest.skip("set RUN_AGENT=1 para tests end-to-end con LLM")
    if not _llm_ready():
        pytest.skip("OPENAI_API_KEY no configurada (dummy detectado)")

    from app.infrastructure.postgres import open_database, close_database

    try:
        await open_database()
    except Exception:
        pytest.skip("DB unavailable")

    try:
        yield
    finally:
        await close_database()


@pytest.fixture
async def persistent_graph():
    """Grafo compilado con checkpointer PostgreSQL (agent DB).

    Gated por RUN_AGENT=1. Skip si la agent DB o el LLM no estan listos.
    """
    if os.environ.get("RUN_AGENT") != "1":
        pytest.skip("set RUN_AGENT=1 para tests de memoria")
    if not _llm_ready():
        pytest.skip("OPENAI_API_KEY no configurada (dummy detectado)")

    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    from app.agent.graph import build_graph
    from app.config import settings
    from app.infrastructure.postgres import close_database, open_database

    cm = None
    try:
        await open_database()
        cm = AsyncPostgresSaver.from_conn_string(settings.agent_database_url)
        checkpointer = await cm.__aenter__()
        await checkpointer.setup()
    except Exception:
        if cm is not None:
            try:
                await cm.__aexit__(None, None, None)
            except Exception:
                pass
        try:
            await close_database()
        except Exception:
            pass
        pytest.skip("agent DB unavailable")

    graph = build_graph(checkpointer)
    try:
        yield graph
    finally:
        try:
            await cm.__aexit__(None, None, None)
        except Exception:
            pass
        await close_database()