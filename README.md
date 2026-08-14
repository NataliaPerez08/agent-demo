# Data Analyst Agent

Agente que recibe preguntas en lenguaje natural sobre datos de ventas,
las convierte en SQL seguro, consulta la base analítica y responde
manteniendo contexto conversacional.

- **API**: FastAPI + LangGraph
- **Modelos**: LiteLLM (gateway a OpenAI gpt-5 / gpt-5-mini)
- **Datos analíticos**: PostgreSQL (rol read-only `analyst_agent`)
- **Memoria / checkpoints**: PostgreSQL (agent DB)
- **Sesiones / caché / rate limit**: Redis
- **Validación SQL**: SQLGlot (AST + whitelist de esquemas + timeout)

---

## Arquitectura

```text
Usuario
   │  HTTP
   ▼
FastAPI + LangGraph  ──► LiteLLM ──► modelos (gpt-5 / gpt-5-mini)
   │
   ├──► PostgreSQL (analytics)  · datos + views + rol read-only
   ├──► PostgreSQL (agent)      · checkpoints + auditoría
   └──► Redis                   · sesiones · caché schema/query · rate limit
```

Pipeline del agente:

```text
question → retrieve_schema → generate_sql → validate_sql
                                              │  inválido → fix_sql → (revalida)
                                              ▼  válido
                                         execute_sql
                                              │  error → fix_sql → (revalida)
                                              ▼  ok
                                       analyze_results → generate_answer
```

- Máximo **2 retries** de self-healing.
- Trazabilidad por request (timings por fase, tokens, coste y `request_id` en auditoría).

---

## Requisitos

- Docker + Docker Compose
- `OPENAI_API_KEY` válida (la consumen los modelos vía LiteLLM)

---

## Puesta en marcha

1. Copiar variables y setear la API key de OpenAI:

   ```bash
   cp .env.example .env
   # editar .env y poner un valor real en OPENAI_API_KEY
   ```

2. Levantar el stack:

   ```bash
   docker compose up --build
   ```

   Esto levanta: `api`, `postgres` (agent DB), `analytics` (datos), `redis`
   y `litellm`. Los DDL y el seed se inicializan automáticamente en la
   `analytics` DB, y el rol read-only `analyst_agent` + la tabla de
   auditoría en la `agent` DB.

3. Health check:

   ```bash
   curl http://localhost:8000/health
   # {"status":"ok"}
   ```

4. Preguntar:

   ```bash
   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"question": "¿Cuáles fueron los 5 clientes con más revenue?"}'
   ```

   Respuesta:

   ```json
   {
     "thread_id": "...",
     "answer": "Los cinco clientes con mayor revenue fueron...",
     "sql": "SELECT ..."
   }
   ```

El mismo `user_id` reutiliza el `thread_id` (sesión en Redis) →
**follow-ups** conversacionales:

```text
Usuario: ¿Cuáles fueron los mejores clientes?
Agente: ...
Usuario: ¿Y solo los de México?
Agente: ...  (entiende el contexto)
```

---

## Endpoints

| Método | Ruta     | Descripción                                  |
|--------|----------|----------------------------------------------|
| GET    | `/health`| Status del servicio                          |
| POST   | `/chat`  | Pregunta al agente (devuelve answer + sql)   |

### Request `/chat`

```json
{
  "question": "¿Cuánto revenue hubo en julio?",
  "user_id": "user-123"
}
```

### Response

```json
{
  "thread_id": "uuid",
  "answer": "...",
  "sql": "SELECT ..."
}
```

`user_id` opcional (default `anon`). Rate limit: 30 peticiones/min por
usuario (fail-open si Redis no responde).

---

## Estructura del repositorio

```text
app/
├── main.py                     FastAPI + lifespan (DB + checkpointer)
├── config.py                   Settings (env)
├── agent/
│   ├── state.py                AnalystState (TypedDict)
│   ├── routing.py              routing condicional (validate/execute)
│   └── graph.py                StateGraph (build_graph(checkpointer))
├── nodes/
│   ├── schema.py               retrieve_schema (+ caché Redis)
│   ├── generate_sql.py         LLM → SQL
│   ├── validate_sql.py         SQLGlot AST validator
│   ├── execute_sql.py          pool async + timeout + MAX_ROWS + caché
│   ├── fix_sql.py              self-healing
│   ├── analyze.py              análisis de resultados
│   ├── answer.py               respuesta final
│   └── failure.py              nodo terminal
├── api/
│   ├── routes.py               POST /chat
│   └── schemas.py              ChatRequest / ChatResponse
├── infrastructure/
│   ├── postgres.py             pools + AsyncPostgresSaver (checkpointer)
│   ├── redis.py               caché/sesión/rate-limit (fail-open)
│   ├── llm.py                 get_llm + ainvoke_with_usage (tokens)
│   ├── audit.py                log_query → analytics_query_log
│   └── observability.py        Observation (contextvar), timed, reporte
└── eval/
    ├── metrics.py              métricas por dimensión
    └── evaluator.py           run_dataset + summarize + reporte

database/
├── analytics/                  datos de negocio (rol read-only)
│   ├── ddl/  (schema, indexes, views, agent_role)
│   ├── dml/  (seed)
│   └── model/ (data_dictionary.yaml, erd.md)
└── agent/                      checkpoints + auditoría
    └── ddl/  (001_audit.sql)

eval/dataset.yaml               dataset de evaluación (6 casos)
litellm/config.yaml             modelos analyst-fast / analyst-smart
tests/  (unit, integration, agent)
```

---

## Seguridad del SQL

Capas (defensa en profundidad):

1. **LLM** con prompt read-only.
2. **SQLGlot AST**: bloquea `INSERT/UPDATE/DELETE/DROP/CREATE/ALTER/
   TRUNCATE/COPY`, multi-statement, `pg_sleep`, `dblink`, etc.
3. **Whitelist de esquemas**: `pg_catalog` e `information_schema`
   bloqueados.
4. **Conexión read-only** pool (`SET LOCAL statement_timeout`).
5. **Rol PostgreSQL read-only** `analyst_agent`.
6. **`statement_timeout`** 5 s y **`MAX_ROWS`** 100.

---

## Tests

```bash
# Unitarios (sin infra) — siempre
py -m pytest tests/unit -q

# Toda la suite (integration/agent se saltan sin DB/LLM)
py -m pytest tests -q
```

Tests de **integración** y **agente** requieren servicios levantados.
Para activarlos (gated, evitan coste accidental):

```bash
# DB disponibles (docker compose up) + API key real:
$env:RUN_AGENT="1"           # PowerShell  (export RUN_AGENT=1 en *nix)
$env:OPENAI_API_KEY="sk-..."
py -m pytest tests -q
```

| Suite            | Requiere               | Marker        |
|------------------|------------------------|---------------|
| unit             | nada                   | —             |
| integration      | analytics/agent DB     | `integration` |
| agent (e2e/eval) | DB + LLM + `RUN_AGENT=1` | `agent`     |

---

## Evaluación

Dataset en `eval/dataset.yaml` (6 preguntas con `expected_tables`,
`expected_metric`, `expected_filters`, `expected_result`,
`expected_contains`):

```bash
RUN_AGENT=1 py -m pytest tests/agent/test_eval.py -s
```

Mide por caso: `tables_ok`, `metric_ok`, `filters_ok`, `result_ok`,
`answer_ok`, `latency_ms`, `retries`. El reporte se imprime en consola.

---

## Observabilidad

Por request (vía contextvar, aislada/thread-safe):

```text
request: <request_id>
schema=20ms  generate_sql=820ms  validate_sql=4ms  execute_sql=34ms  analyze=600ms  answer=390ms
total=1868ms
tokens in=2100 out=140 total=2240 cost=$0.000105
```

Correlacionado con `analytics_query_log` (`request_id`).

---

## Variables de entorno

Definidas en `.env` (ver `.env.example`):

| Variable                  | Descripción                              |
|---------------------------|------------------------------------------|
| `OPENAI_API_KEY`          | API key de OpenAI (consumo vía LiteLLM)  |
| `LITELLM_MASTER_KEY`      | Master key del gateway LiteLLM           |
| `LITELLM_BASE_URL`        | URL del gateway (interno en compose)     |
| `AGENT_DATABASE_URL`      | PostgreSQL del agente (checkpoints+audit)|
| `ANALYTICS_DATABASE_URL`  | PostgreSQL analítica (rol read-only)     |
| `REDIS_URL`               | URL de Redis                             |

---

## Plan de acción

El desarrollo sigue `action_plan.md`. Estado:
Fases 1–18 completadas (MVP + conversacional + confiabilidad).
Ver `git log` para el histórico por etapa.