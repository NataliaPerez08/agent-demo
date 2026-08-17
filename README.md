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
| POST   | `/chat`  | Pregunta al agente (devuelve answer + sql + chart) |
| GET    | `/export`| Descarga el último resultado en CSV o XLSX     |

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
  "sql": "SELECT ...",
  "chart": {
    "type": "bar",
    "title": "Top clientes",
    "x": "name",
    "y": "revenue",
    "series": null,
    "columns": ["name", "revenue"]
  }
}
```

`user_id` opcional (default `anon`). Rate limit: 30 peticiones/min por
usuario (fail-open si Redis no responde).

### Export (`/export`)

Descarga el último resultado de un `thread_id` (cacheado en Redis, TTL 1h):

```bash
# CSV
curl -o results.csv "http://localhost:8000/export?thread_id=<uuid>&fmt=csv"

# Excel
curl -o results.xlsx "http://localhost:8000/export?thread_id=<uuid>&fmt=xlsx"
```

| Parámetro    | Tipo | Default | Descripción                              |
|--------------|------|---------|------------------------------------------|
| `thread_id`  | str  | —       | `thread_id` devuelto por `/chat` (req.)  |
| `fmt`        | str  | `csv`   | `csv` o `xlsx`                           |

### Charts

`/chat` devuelve además `chart`: una sugerencia de visualización heurística
derivada de los resultados (no requiere LLM extra). Tipos:

- `line`  — eje temporal + 1 métrica
- `bar`   — 1 categoría + 1..N métricas
- `pie`   — 1 categoría + 1 métrica (≤6 filas)

Columnas tipo `id`/`*_id` se excluyen como métricas. Si no encaja ningún
patrón, `chart` es `null` (los datos se muestran como tabla).

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
│   ├── routes.py               POST /chat + GET /export
│   └── schemas.py              ChatRequest/Response + ChartConfig
├── services/
│   ├── export.py               rows → CSV / XLSX
│   └── charts.py               suggest_chart (line/bar/pie)
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

Unitarios cubren: validador SQL (18 casos), observabilidad (timings,
tokens, coste), **export CSV/XLSX** y **sugerencia de charts**
(line/bar/pie).
### Tests con modelo local (Ollama, sin API key)

`docker compose up` ya descarga y verifica los modelos de Ollama
automáticamente (`ollama-init` con healthcheck y smoke test). Una vez
levantado el stack, correr los tests e2e contra el modelo local:

```bash
# Linux/macOS (Makefile)
make test-local
# o todo en uno (levanta ollama + DBs, corre tests, baja al finish):
make test-local-up

# Windows (PowerShell)
.\scripts\test-local.ps1 -Up -Down
# o si el stack ya esta levantado:
.\scripts\test-local.ps1
```

Esto setea `ANALYST_MODEL=analyst-local-fast` (qwen2.5:1.5b) y
`RUN_AGENT=1`. El `conftest` probea `http://localhost:11434/api/tags`
para confirmar que el modelo esté cargado antes de correr (skip limpio
si no lo está).

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
| `ANALYST_MODEL`           | Alias de modelo (`analyst-smart` por defecto; ver Ollama) |

---

## Modelos locales con Ollama (sin API key, sin coste)

El stack incluye un servicio **Ollama** que LiteLLM expone como modelos
alternativos. Para usarlos, define en `.env`:

```env
ANALYST_MODEL=analyst-local        # qwen2.5:7b  (capaz)
# o
ANALYST_MODEL=analyst-local-fast   # qwen2.5:1.5b (ligero)
```

`docker compose up --build` levanta además `ollama-init`, que descarga los
modelos la **primera vez** (puede tardar varios minutos según conexión).
Las llamadas al agente fallarán con 404 hasta que los modelos estén listos;
luego funcionan sin `OPENAI_API_KEY`.

> Nota: en CPU los modelos grandes son lentos. Para GPU, monta el dispositivo
> en el servicio `ollama` del compose (ver [docs de Ollama](https://github.com/ollama/ollama)).

Aliases disponibles (definidos en `litellm/config.yaml`):

| Alias                | Backend          | Notas                          |
|----------------------|------------------|--------------------------------|
| `analyst-smart`      | OpenAI gpt-5     | default, requiere API key      |
| `analyst-fast`       | OpenAI gpt-5-mini| rápido, requiere API key        |
| `analyst-local`      | Ollama qwen2.5:7b | local, sin coste              |
| `analyst-local-fast` | Ollama qwen2.5:1.5b | local, ligero               |

---

## Plan de acción

El desarrollo sigue `action_plan.md`. Estado:

- **Fases 1–18** completadas (MVP + conversacional + confiabilidad).
- **Etapa D** en curso (rama `etapa-d`): export CSV/Excel + charts ✅.
  Pendientes: métricas, RAG, reportes programados, auth empresarial.

Ver `git log` para el histórico por etapa.