import os

# Defaults apuntan a los puertos publicados en host por docker-compose.
# Solo se aplican si la variable no esta definida previamente, asi que
# un .env o un entorno CI pueden sobreescribirlos.
os.environ.setdefault("LITELLM_BASE_URL", "http://localhost:4000/v1")
os.environ.setdefault("LITELLM_MASTER_KEY", "sk-local-secret")
os.environ.setdefault("AGENT_DATABASE_URL", "postgresql://agent:agent@localhost:5432/agent")
os.environ.setdefault("ANALYTICS_DATABASE_URL", "postgresql://analyst_agent:analyst@localhost:5433/analytics")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("ANALYST_MODEL", "analyst-smart")

import json
import urllib.request

import pytest


# Alias de LiteLLM -> tag de Ollama.
OLLAMA_TAG_BY_ALIAS = {
    "analyst-local": "qwen2.5:7b",
    "analyst-local-fast": "qwen2.5:1.5b",
}

OLLAMA_HOST_DEFAULT = "http://localhost:11434"


async def _can_connect(url: str) -> bool:
    """Probe con una conexion efimera (no toca el pool global).

    Usar el pool global aqui abriria/cerraria la misma instancia que luego
    usan las fixtures, provocando PoolClosed al reutilizarla.
    """
    from psycopg import AsyncConnection

    try:
        conn = await AsyncConnection.connect(url)
        try:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                await cur.fetchone()
        finally:
            await conn.close()
        return True
    except Exception:
        return False


def _local_model_ready() -> bool:
    """True si el modelo local configurado esta cargado en Ollama.

    Probe via /api/tags (stdlib, sin dependencias). Tolerante: cualquier
    fallo de conexion devuelve False.
    """

    model = os.environ.get("ANALYST_MODEL", "")
    tag = OLLAMA_TAG_BY_ALIAS.get(model)

    if not tag:
        return False

    host = os.environ.get("OLLAMA_HOST", OLLAMA_HOST_DEFAULT)

    try:
        with urllib.request.urlopen(f"{host}/api/tags", timeout=2) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return False

    loaded = {m.get("name", "") for m in payload.get("models", [])}
    return any(tag in name for name in loaded)


def _is_local_model() -> bool:
    return os.environ.get("ANALYST_MODEL", "").startswith("analyst-local")


def _llm_ready() -> bool:
    """True si el LLM configurado esta listo para usarse.

    - Modelos locales (analyst-local*): probea Ollama via /api/tags.
    - Modelos OpenAI: requiere OPENAI_API_KEY no dummy.
    """

    if _is_local_model():
        return _local_model_ready()

    key = os.environ.get("OPENAI_API_KEY", "")
    return bool(key) and key != "TU_API_KEY"


@pytest.fixture
async def analytics_pool_ready():
    """Abre el pool de analytics y hace skip si la DB no esta disponible."""
    from app.config import settings

    if not await _can_connect(settings.analytics_database_url):
        pytest.skip("analytics DB unavailable (levantar docker compose)")

    from app.infrastructure.postgres import analytics_pool

    await analytics_pool.open()
    try:
        yield analytics_pool
    finally:
        await analytics_pool.close()


async def _can_connect_agent() -> bool:
    from app.config import settings

    return await _can_connect(settings.agent_database_url)


@pytest.fixture
async def agent_db_ready():
    """Abre el pool de la agent DB y hace skip si no esta disponible."""
    if not await _can_connect_agent():
        pytest.skip("agent DB unavailable (levantar docker compose)")

    from app.infrastructure.postgres import agent_pool

    await agent_pool.open()
    try:
        yield agent_pool
    finally:
        await agent_pool.close()


@pytest.fixture
async def full_stack():
    """Requiere LLM + DB. Gated por RUN_AGENT=1 para evitar coste accidental."""
    if os.environ.get("RUN_AGENT") != "1":
        pytest.skip("set RUN_AGENT=1 para tests end-to-end con LLM")
    if not _llm_ready():
        if _is_local_model():
            pytest.skip("modelo local no cargado (levantar ollama + ollama-init)")
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
        if _is_local_model():
            pytest.skip("modelo local no cargado (levantar ollama + ollama-init)")
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