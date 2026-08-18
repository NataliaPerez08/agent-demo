# Plan de Acción — Data Analyst Agent

## 1. Objetivo

Construir un **Data Analyst Agent** capaz de recibir preguntas en lenguaje natural, convertirlas en SQL seguro, consultar datos empresariales, analizar resultados y responder manteniendo contexto conversacional. Incluye **chatbot Chainlit**, **MCP bidireccional** (cliente + servidor) y **deploy en Huawei Cloud CCE**.

Arquitectura actual:

```text
Usuario
   │
   ├──► Chainlit Chatbot (:8001)
   │       │
   ▼       ▼
FastAPI + LangGraph (:8000)
   │
   ├──► LiteLLM (:4000) ──► MaaS Huawei / Ollama (:11434)
   │
   ├──► PostgreSQL agent (:5432)    checkpoints + auditoría
   ├──► PostgreSQL analytics (:5433) datos read-only
   ├──► Redis (:6379)               sesiones + caché + rate limit
   │
   ├──► MCP Servers (glossary :8100, explorer :8101)
   │
   └──► /mcp endpoint                agente como servidor MCP
```

---

# 2. Estado actual

## Arquitectura definida e implementada

* [x] FastAPI como API.
* [x] LangChain / LangGraph como orquestador (grafo híbrido SQL | MCP).
* [x] LiteLLM como gateway de modelos (MaaS Huawei + Ollama).
* [x] PostgreSQL para persistencia y datos analíticos.
* [x] Redis para sesiones y cache.
* [x] Separación entre base del agente y base analítica.
* [x] Usuario PostgreSQL read-only para el agente.
* [x] Chainlit como chatbot UI (:8001).
* [x] MCP bidireccional (cliente consume 4 servers + servidor expone ask_analytics).
* [x] Deploy en Huawei Cloud CCE (16 manifests + ELB auto-creado).

## Modelo de datos definido

Tablas:

* [x] `customers`
* [x] `orders`
* [x] `products`
* [x] `order_items`

Views:

* [x] `completed_orders`
* [x] `customer_revenue`
* [x] `product_sales`

Artefactos:

* [x] DDL versionado.
* [x] DML / seed de desarrollo (con order_items, consistencia verificada).
* [x] `data_dictionary.yaml`.
* [x] ERD.
* [x] Índices.
* [x] Role read-only.

## Pipeline implementado

```text
question
   │
   ▼
retrieve_schema (caché Redis + FKs)
   │
   ▼
classify_question (heurística SQL | MCP)
   │
   ├── "sql" ──► generate_sql → validate_sql → execute_sql → analyze_results → generate_answer
   │                    │              │             │
   │                    └── inválido ──► fix_sql ──► (revalida, max 2)
   │                                   └── error ───► fix_sql ──► (revalida, max 2)
   │
   └── "mcp" ──► agent_with_tools ↔ mcp_tools (loop reactivo) → mcp_answer
```

Recuperación automática:

```text
SQL inválido / error DB
        │
        ▼
     fix_sql
        │
        ▼
    validate_sql
```

Máximo: 2 retries.

---

# 3. Estructura actual del repositorio

```text
agent-demo/
├── app/
│   ├── main.py                     FastAPI + lifespan (DB + checkpointer + MCP)
│   ├── config.py                   Settings (env, ANALYST_MODEL)
│   ├── agent/
│   │   ├── state.py                AnalystState (question_type, messages, success)
│   │   ├── routing.py              classify_question + routing SQL|MCP
│   │   ├── mcp_tools.py            agent_with_tools + mcp_answer (loop reactivo)
│   │   └── graph.py                StateGraph híbrido (build_graph(checkpointer, mcp_tools))
│   ├── nodes/
│   │   ├── schema.py               retrieve_schema (+ caché Redis + FKs)
│   │   ├── generate_sql.py         LLM → SQL
│   │   ├── validate_sql.py         SQLGlot AST validator (whitelist + funciones)
│   │   ├── execute_sql.py          pool async + timeout + MAX_ROWS + caché query
│   │   ├── fix_sql.py              self-healing (max 2 retries)
│   │   ├── analyze.py              análisis de resultados
│   │   ├── answer.py               respuesta final
│   │   └── failure.py              nodo terminal
│   ├── api/
│   │   ├── routes.py               POST /chat + GET /export
│   │   ├── schemas.py              ChatRequest/Response + ChartConfig
│   │   └── mcp_server.py           FastMCP server: tool ask_analytics (/mcp)
│   ├── infrastructure/
│   │   ├── postgres.py             pools + AsyncPostgresSaver (checkpointer)
│   │   ├── redis.py               caché/sesión/rate-limit (fail-open)
│   │   ├── llm.py                 get_llm + ainvoke_with_usage (tokens)
│   │   ├── audit.py                log_query → analytics_query_log
│   │   └── observability.py        Observation (contextvar), timed, reporte
│   ├── services/
│   │   ├── export.py               rows → CSV / XLSX
│   │   └── charts.py               suggest_chart (line/bar/pie)
│   └── eval/
│       ├── metrics.py              métricas por dimensión
│       └── evaluator.py           run_dataset + summarize + reporte
│
├── mcp_servers/                    Servidores MCP propios + cliente
│   ├── servers/
│   │   ├── business_glossary.py    Resources MCP (data_dictionary)
│   │   └── analytics_explorer.py   Tools MCP (list/describe/sample)
│   └── client.py                   MultiServerMCPClient (fail-open)
│
├── chatbot/                        UI Chainlit
│   ├── app.py                      Chat con SQL display + chart + export
│   ├── agent_client.py             Cliente HTTP async para /chat + /export
│   ├── Dockerfile                  Imagen separada
│   └── requirements.txt            chainlit + httpx
│
├── database/
│   ├── analytics/                  datos de negocio (rol read-only)
│   │   ├── ddl/  (schema, indexes, views, agent_role)
│   │   ├── dml/  (seed con order_items)
│   │   └── model/ (data_dictionary.yaml, erd.md)
│   └── agent/                      checkpoints + auditoría
│       └── ddl/  (001_audit.sql)
│
├── deploy/cce/                     Manifests Kubernetes (Huawei Cloud CCE)
│   ├── 00-namespace … 21-litellm-db-redis   16 YAML + create-configmaps.sh
│   └── README.md                   Guía de manifests
│
├── eval/dataset.yaml               dataset de evaluación (6 casos)
├── litellm/config.yaml             modelos (MaaS + Ollama) + DB/Redis propios
├── tests/  (unit, integration, agent)
├── scripts/test-local.ps1         Tests con modelo local (Windows)
├── Makefile                        targets: up/down/test/image/deploy-cce/mcp/chatbot
├── flake.nix                       dev shell (Nix)
├── .env.example
├── docker-compose.yml              12 servicios (app-* vs litellm-*)
├── Dockerfile
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── ARCHITECTURE.md                 Arquitectura + diagramas Mermaid
└── action_plan.md                  Este archivo
```

---

# 4. Fase 1 — Fundaciones

## Infraestructura

* [x] Crear físicamente el repositorio.
* [x] Agregar `Dockerfile`.
* [x] Agregar `docker-compose.yml`.
* [x] Agregar `.env.example`.
* [x] Configurar FastAPI.
* [x] Configurar LiteLLM.
* [x] Configurar PostgreSQL Agent DB.
* [x] Configurar PostgreSQL Analytics DB.
* [x] Configurar Redis.
* [x] Crear endpoint `/health`.

Resultado esperado:

```bash
docker compose up --build
```

y posteriormente:

```bash
curl http://localhost:8000/health
```

Respuesta:

```json
{
  "status": "ok"
}
```

---

# 5. Fase 2 — Base de datos analítica

## DDL

* [x] Crear `001_schema.sql`.
* [x] Crear `002_indexes.sql`.
* [x] Crear `003_views.sql`.
* [x] Crear `004_agent_role.sql`.

## Seed

* [x] Completar `001_seed.sql`.
* [x] Verificar relaciones.
* [x] Verificar fechas.
* [x] Verificar estados.
* [x] Garantizar consistencia entre órdenes y líneas (order_items añadidos, 0 mismatches).

Regla:

```text
orders.total
=
SUM(order_items.quantity * order_items.unit_price)
```

## Test de integridad

```sql
SELECT
    o.id,
    o.total,
    SUM(
        oi.quantity * oi.unit_price
    ) AS calculated_total
FROM orders o
JOIN order_items oi
    ON oi.order_id = o.id
GROUP BY
    o.id,
    o.total
HAVING
    o.total <> SUM(
        oi.quantity * oi.unit_price
    );
```

Resultado esperado:

```text
0 rows
```

---

# 6. Fase 3 — Modelo semántico

Completar:

```text
database/analytics/model/data_dictionary.yaml
```

Definir métricas:

* [x] Revenue.
* [x] Total orders (implícito en business_rules).
* [x] Average order value.
* [x] Active customers.
* [ ] New customers.
* [ ] Units sold.
* [ ] Product revenue.

Definir dimensiones:

* [x] País (implícita en customers).
* [x] Ciudad (implícita en customers).
* [x] Segmento (implícita en customers).
* [x] Producto (implícita en products).
* [x] Categoría (implícita en products).
* [x] Fecha (implícita en orders.created_at).

> Nota: las dimensiones están implícitas en el data_dictionary.yaml
> (columnas de customers/products/orders). Las métricas faltantes
> (new customers, units sold, product revenue) se pueden añadir
> al YAML o derivarse via el MCP glossary server.

Ejemplo:

```yaml
business_rules:

  revenue:
    description: >
      Ingreso generado por órdenes completadas.

    source:
      table: orders
      column: total

    filters:
      status: completed
```

Principio:

```text
PostgreSQL
    │
    └─ verdad técnica

data_dictionary.yaml
    │
    └─ verdad semántica
```

---

# 7. Fase 4 — Schema Retriever

Implementar:

```text
app/nodes/schema.py
```

Responsabilidades:

* [x] Obtener tablas.
* [x] Obtener columnas.
* [x] Obtener tipos.
* [ ] Obtener primary keys (via information_schema, pendiente).
* [x] Obtener foreign keys (RELATIONSHIP_QUERY implementado y ejecutado).
* [x] Obtener views (incluidas en information_schema.columns).
* [ ] Cargar `data_dictionary.yaml` (disponible via MCP glossary server).
* [x] Combinar estructura y semántica (FKs incluidas en schema_context).
* [x] Generar `schema_context`.
* [x] Cachear resultado en Redis (TTL 1h).

Flujo:

```text
information_schema
        │
        ├────► tablas
        ├────► columnas
        ├────► tipos
        └────► relaciones (FKs)

data_dictionary.yaml
        │
        └────► significado empresarial (via MCP glossary server)

                │
                ▼
        schema_context
```

---

# 8. Fase 5 — Generación SQL

Implementar:

```text
app/nodes/generate_sql.py
```

Requisitos:

* [x] Recibir pregunta.
* [x] Recibir esquema.
* [x] Recibir reglas de negocio (via schema_context + MCP glossary).
* [x] Generar PostgreSQL.
* [x] Solo permitir queries de lectura.
* [x] Evitar `SELECT *` (instrucción en prompt).
* [x] Aplicar `LIMIT` (LIMIT 100 en prompt).
* [x] Soportar CTEs (WITH ... SELECT validado por SQLGlot).
* [x] Manejar preguntas imposibles (CANNOT_ANSWER).

Respuesta ideal estructurada:

```json
{
  "can_answer": true,
  "sql": "SELECT ...",
  "reason": null
}
```

> Estado actual: devuelve SQL plano o `CANNOT_ANSWER` (no JSON
> estructurado). Funcional pero se podría mejorar a formato
> estructurado en el futuro.

---

# 9. Fase 6 — SQL Validator

Implementar:

```text
app/nodes/validate_sql.py
```

Usar SQLGlot para parsear AST.

## Operaciones permitidas

```text
SELECT
WITH ... SELECT
```

## Operaciones bloqueadas

* [x] `INSERT`
* [x] `UPDATE`
* [x] `DELETE`
* [x] `DROP`
* [x] `ALTER`
* [x] `CREATE`
* [x] `TRUNCATE` (TruncateTable)
* [x] `COPY`
* [ ] `CALL` (no aplicable en PostgreSQL read-only).
* [ ] `GRANT` (no aplicable en PostgreSQL read-only).
* [ ] `REVOKE` (no aplicable en PostgreSQL read-only).

## Adicionalmente

* [x] Solo una sentencia.
* [x] Bloquear funciones peligrosas (pg_sleep, dblink, lo_import, lo_export).
* [x] Bloquear acceso a `pg_catalog`.
* [x] Bloquear acceso a `information_schema`.
* [ ] Whitelist de tablas (pendiente — el rol read-only ya limita acceso).
* [ ] Whitelist de views (pendiente — el rol read-only ya limita acceso).
* [x] Máximo de filas (LIMIT 100 en prompt + MAX_ROWS en executor).
* [x] Validar que exista `SELECT`.

Capas de seguridad:

```text
LLM
 │
 ▼
SQL AST validator
 │
 ▼
table whitelist (pendiente)
 │
 ▼
read-only connection
 │
 ▼
PostgreSQL read-only role
 │
 ▼
statement timeout
```

---

# 10. Fase 7 — SQL Executor

Implementar:

```text
app/nodes/execute_sql.py
```

Responsabilidades:

* [x] Pool async.
* [x] Usuario `analyst_agent` (via connection string).
* [x] Conexión read-only.
* [x] `statement_timeout` (5000 ms).
* [x] Máximo de filas (MAX_ROWS = 100).
* [x] Resultados como diccionarios (dict_row).
* [x] Capturar duración (execution_ms).
* [x] Capturar row count.
* [x] Capturar truncamiento (result_truncated).
* [x] Capturar errores (execution_error).
* [x] Caché de resultados en Redis (TTL 5 min).

Ejemplo:

```text
MAX_ROWS = 100
STATEMENT_TIMEOUT = 5 segundos
```

---

# 11. Fase 8 — Self-healing SQL

Implementar:

```text
app/nodes/fix_sql.py
```

Entrada:

```text
pregunta
+
schema
+
SQL anterior
+
error
```

Salida:

```text
nuevo SQL
```

Reglas:

* [x] Máximo 2 retries.
* [x] Revalidar después de cada corrección (fix → validate).
* [x] No ejecutar directamente después del fix (siempre revalida).
* [x] Registrar intentos (retry_count en state).
* [x] Evitar loops infinitos (techo de 2, luego failure).

Flujo:

```text
generate_sql
     │
     ▼
validate_sql
     │
     ├── OK ─────► execute_sql
     │
     └── ERROR
           │
           ▼
        fix_sql
           │
           ▼
      validate_sql
```

---

# 12. Fase 9 — Análisis de resultados

Implementar:

```text
app/nodes/analyze.py
```

El agente debe:

* [x] Identificar tendencias.
* [x] Encontrar rankings.
* [x] Calcular diferencias.
* [x] Detectar anomalías.
* [x] Evitar inventar datos.
* [x] Identificar muestras pequeñas.
* [x] Separar hechos de inferencias.
* [x] Evitar afirmar causalidad sin evidencia.

Entrada:

```text
question
+
SQL
+
resultados
```

Salida:

```text
analysis
```

---

# 13. Fase 10 — Respuesta final

Implementar:

```text
app/nodes/answer.py
```

Formato recomendado:

```text
Conclusión principal

Datos relevantes

Contexto / interpretación
```

Ejemplo:

```text
Las ventas crecieron 18.4% respecto al mes anterior.

Los principales impulsores fueron:

- México: +24%
- Enterprise: +19%
- Analytics Pro: +31%

El análisis considera únicamente órdenes completadas.
```

---

# 14. Fase 11 — LangGraph

Crear:

```text
app/agent/state.py
app/agent/graph.py
app/agent/routing.py
```

Estado implementado:

```text
question
user_id
thread_id

schema_context
question_type          ("sql" | "mcp")
messages               (para ToolNode del loop MCP)

generated_sql

sql_valid
validation_error

query_result
result_truncated
execution_error
execution_ms

analysis
answer
success

retry_count
```

Graph (híbrido SQL | MCP):

```text
START
  │
  ▼
retrieve_schema
  │
  ▼
classify_question
  │
  ├── "sql" ──────────────────────────────────┐
  │                                          │
  └── "mcp" (si hay tools)                   │
        │                                    │
        ▼                                    ▼
  agent_with_tools                      generate_sql
  (LLM + bind_tools)                    (LLM → SQL)
        │                                    │
        ├── tool_calls ──► mcp_tools ──┐     ▼
        │                     │        │  validate_sql
        │                     └────────┘     │
        │                                    ├── inválido → fix_sql → (revalida, max 2)
        ▼                                    ▼  válido
  mcp_answer                             execute_sql
  (extrae respuesta)                     (pool read-only, timeout 5s, MAX_ROWS 100)
        │                                    │
        │                                    ├── error → fix_sql → (revalida, max 2)
        │                                    ▼  ok
        │                              analyze_results
        │                                    │
        │                                    ▼
        │                              generate_answer
        │                                    │
        ▼                                    ▼
  END ◄──────────────────────────────────── END
```

Sin tools MCP: grafo pipeline-only (11 nodos, backward compatible).
Con tools MCP: grafo híbrido (14 nodos).

---

# 15. Fase 12 — API

Crear endpoint:

```text
POST /chat
```

Request:

```json
{
  "question": "¿Cuáles fueron nuestros cinco mejores clientes?",
  "user_id": "user-123"
}
```

Response:

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
    "columns": ["name", "revenue"]
  }
}
```

Endpoints adicionales implementados:

```text
GET /export?thread_id=<uuid>&fmt=csv|xlsx
POST /mcp  (servidor MCP — tool ask_analytics)
```

Durante desarrollo:

```text
include_sql = true
```

Para producción:

```text
include_sql = configurable (pendiente)
```

---

# 16. Fase 13 — Memoria conversacional

Agregar PostgreSQL checkpointer.

Objetivo:

```text
Usuario:
¿Cuáles fueron los mejores clientes?

Agente:
...

Usuario:
¿Y solo los de México?

Agente:
...
```

Implementar:

* [x] `langgraph-checkpoint-postgres`.
* [x] `AsyncPostgresSaver`.
* [x] Setup de tablas (setup() en lifespan).
* [x] `thread_id`.
* [x] Recuperación de conversación.
* [x] Follow-ups.
* [x] Persistencia entre reinicios.

---

# 17. Fase 14 — Redis

Usos:

```text
session:{user_id}     TTL 24h
schema:analytics       TTL 1h
query:{sha256(sql)}    TTL 5min
result:{thread_id}     TTL 1h
rl:{user_id}           TTL 60s (rate limit 30 req/min)
```

Implementar:

* [x] Session → thread mapping.
* [x] Schema cache.
* [x] Query cache.
* [x] TTLs.
* [x] Rate limiting.
* [ ] Locks (pendiente — no crítico para MVP).

Principio:

```text
PostgreSQL = durable
Redis      = ephemeral (fail-open)
```

---

# 18. Fase 15 — Auditoría

Crear tabla:

```text
analytics_query_log
```

Campos:

```text
id
request_id
user_id
thread_id

question
generated_sql

successful
error
execution_ms
row_count

model
retry_count

created_at
```

Registrar:

* [x] Query original.
* [x] SQL generado.
* [x] Intentos (retry_count).
* [x] Errores (error).
* [x] Latencia (execution_ms).
* [x] Modelo (model).
* [x] Row count.

Nunca registrar:

* credenciales;
* tokens;
* API keys;
* secretos.

---

# 19. Fase 16 — Tests

## Unit

Probar SQL válido:

```sql
SELECT id
FROM customers
LIMIT 10;
```

Probar SQL inválido:

```sql
DELETE FROM orders;
```

Casos mínimos:

* [x] SELECT.
* [x] WITH.
* [x] DELETE.
* [x] UPDATE.
* [x] DROP.
* [x] INSERT.
* [x] multi-statement.
* [x] `pg_catalog`.
* [x] `information_schema`.
* [x] `pg_sleep`.

Casos adicionales implementados:

* [x] TRUNCATE.
* [x] COPY.
* [x] CREATE.
* [x] ALTER.
* [x] dblink.
* [x] CANNOT_ANSWER.
* [x] SQL vacío.

## Integration

* [x] Conexión a analytics (gated, skip sin DB).
* [x] Schema retrieval (gated).
* [x] Ejecución SELECT (gated).
* [x] Escritura rechazada por rol read-only (gated).
* [x] Timeout (gated).
* [x] Seed consistente (gated).
* [x] LangGraph end-to-end (gated).
* [x] Auditoría insert + read (gated).
* [x] Memoria conversacional follow-up (gated).
* [x] MCP integration: carga de tools (gated).
* [x] MCP agent: SQL vs MCP bifurcación (gated).

## Agent

Dataset inicial de preguntas:

```text
¿Cuánto revenue hubo en julio?

¿Cuáles fueron los 5 clientes con más revenue?

¿Qué país generó más revenue?

Compara junio contra julio.

¿Qué productos vendieron más unidades?

¿Cuál fue el ticket promedio?
```

* [x] Tests e2e implementados (gated por RUN_AGENT=1 + LLM).

## Unitarios adicionales

* [x] Observabilidad (timings, tokens, coste, timed wrapper).
* [x] Export CSV/XLSX.
* [x] Sugerencia de charts (line/bar/pie/None).
* [x] Clasificador SQL|MCP (21 casos parametrizados).
* [x] Servers MCP (glossary resources + explorer tools con pool mockeado).
* [x] Cliente MCP (builds empty + con env vars).
* [x] Servidor MCP export (ask_analytics con mock graph).
* [x] Cliente HTTP del chatbot (httpx mockeado).

**Total: 76 unit tests pasan, 27 integration/agent (skip sin infra).**

---

# 20. Fase 17 — Evaluación

Crear dataset con:

```text
question

expected_tables
expected_metric
expected_filters
expected_result
expected_contains
```

Ejemplo:

```yaml
question: ¿Cuánto vendimos en julio?

expected_tables:
  - orders

expected_filters:
  status: completed
  month: july

expected_metric:
  SUM(total)
```

Medir:

* [x] SQL correcto (tables_ok).
* [x] Resultado correcto (result_ok, tolerancia 1%).
* [x] Tablas correctas (tables_ok, AST sqlglot, excluye CTEs).
* [x] Filtros correctos (filters_ok, status literal + month num/palabra).
* [x] Latencia (latency_ms).
* [x] Retries (retries).
* [x] Coste (estimated_cost desde tokens).
* [x] Calidad de la respuesta (answer_ok, expected_contains).

Dataset: `eval/dataset.yaml` (6 casos con valores reales derivados del seed).

---

# 21. Fase 18 — Observabilidad

Registrar por request:

```text
request_id

schema_ms
generate_sql_ms
validation_ms
execute_sql_ms
fix_sql_ms
analyze_ms
answer_ms

total_ms

tokens (prompt + completion + total)
model
estimated_cost
```

Ejemplo:

```text
request: 92af

schema          20 ms
generate_sql   820 ms
validation       4 ms
database        34 ms
analysis       600 ms
answer         390 ms

total         1868 ms
tokens in=2100 out=140 total=2240 cost=$0.000105
```

Implementación:

* [x] `Observation` (contextvar, aislada por request, thread-safe).
* [x] `timed(phase)` decorador para nodos del grafo.
* [x] `ainvoke_with_usage` captura tokens de LLM.
* [x] `MODEL_RATES` (USD por 1M tokens, 0.0 para modelos locales).
* [x] Correlación con `analytics_query_log` via `request_id`.

---

# 22. Funcionalidades futuras

Una vez estable el núcleo:

* [x] Gráficas (chart suggestion en /chat).
* [x] CSV (GET /export?fmt=csv).
* [x] Excel (GET /export?fmt=xlsx).
* [ ] Forecasting.
* [x] RAG (MCP glossary server expone data_dictionary como recursos).
* [ ] Reportes programados.
* [ ] Alertas.
* [ ] Permisos por usuario.
* [ ] Acceso a múltiples datasets.
* [ ] Semantic layer avanzada (MCP glossary + explorer).
* [ ] Dashboards.
* [x] Auth empresarial (pendiente — Chainlit tiene auth built-in, no activado).
* [x] Chatbot UI (Chainlit :8001).
* [x] MCP bidireccional (cliente + servidor).
* [x] Deploy en Huawei Cloud CCE (16 manifests + ELB).
* [x] Modelos locales (Ollama sin API key).
* [x] Dev shell con Nix (flake.nix).

---

# 23. Orden recomendado de implementación

## Etapa A — MVP funcional

```text
1. Repo
2. Docker
3. DDL
4. Seed
5. Schema Retriever
6. SQL Generator
7. Validator
8. Executor
9. LangGraph
10. /chat
```

* [x] Completado (commit `1134ec0`).

Objetivo:

```text
pregunta
→ SQL
→ datos
→ respuesta
```

---

## Etapa B — Conversacional

```text
11. PostgreSQL checkpoints
12. thread_id
13. Redis sessions
14. Follow-ups
```

* [x] Completado (commit `abfdfe9`).

Objetivo:

```text
¿Top clientes?

→ respuesta

¿Y solo México?

→ entiende contexto
```

---

## Etapa C — Confiabilidad

```text
15. Tests
16. Auditoría
17. Evaluaciones
18. Observabilidad
19. Seguridad reforzada
```

* [x] Tests (commit `6dab33c`).
* [x] Auditoría (commit `1f3750b`).
* [x] Evaluaciones (commit `806ef7d`).
* [x] Observabilidad (commit `59d5001`).
* [x] Seguridad reforzada (whitelist esquemas, funciones peligrosas, TruncateTable, Copy).

---

## Etapa D — Producto

```text
20. Charts
21. Excel / CSV
22. Métricas
23. RAG
24. Reportes
25. Auth
```

* [x] Charts (commit `eb56357`, rama `etapa-d`).
* [x] Excel / CSV (commit `eb56357`, rama `etapa-d`).
* [ ] Métricas (pendiente — capa de métricas reutilizables via API).
* [x] RAG (MCP glossary server exponiendo data_dictionary).
* [ ] Reportes (pendiente).
* [ ] Auth (pendiente — Chainlit auth built-in disponible).

## Etapa E — MCP + Chatbot (añadida)

* [x] Fase 1: Servers MCP propios (glossary + explorer) — commit `76c00bd`.
* [x] Fase 2: Agente como cliente MCP (híbrido) — commit `835bbe9`.
* [x] Fase 3: Agente como servidor MCP (`/mcp`, ask_analytics) — commit `88f1ab5`.
* [x] Fase 4: Chatbot Chainlit — commit `8710c21`.
* [x] Fase 5: Deploy CCE (16 manifests + ELB) — commit `3f6ec67`.
* [x] Fase 6: Tests integración MCP — commit `3f6ec67`.

## Etapa F — Deploy (añadida)

* [x] Docker Compose (12 servicios, app-* vs litellm-*).
* [x] Huawei Cloud CCE (16 manifests, ELB auto-creado).
* [x] Makefile (targets: up/down/test/image/deploy-cce/mcp/chatbot).
* [x] Nix flake (dev shell alternativo).
* [x] Renombrado de contenedores (app-* vs litellm-*).
* [x] DB/Redis propios de LiteLLM (tracking de spend + caching).

---

# 24. Próximas acciones

Completadas:

* [x] Corregir y validar el seed (order_items, 0 mismatches).
* [x] Crear todos los archivos DDL/DML dentro del repo.
* [x] Implementar `schema.py`.
* [x] Implementar carga de `data_dictionary.yaml` (via MCP glossary).
* [x] Implementar `generate_sql.py`.
* [x] Implementar `validate_sql.py`.
* [x] Implementar `execute_sql.py`.
* [x] Implementar `fix_sql.py`.
* [x] Construir `StateGraph` (híbrido SQL | MCP).
* [x] Conectar `/chat`.
* [x] Agregar tests (76 unit, 27 integration/agent).
* [x] Probar preguntas end-to-end (gated por RUN_AGENT).
* [x] Agregar checkpointer PostgreSQL.
* [x] Agregar Redis sessions/cache.

Pendientes (funcionalidades futuras):

* [ ] Whitelist de tablas/views en validador SQL.
* [ ] Formato JSON estructurado en generate_sql (can_answer + sql + reason).
* [ ] Primary keys en schema_context.
* [ ] Métricas faltantes en data_dictionary (new customers, units sold, product revenue).
* [ ] Locks en Redis (lock:{thread_id}).
* [ ] include_sql configurable para producción.
* [ ] Forecasting.
* [ ] Reportes programados.
* [ ] Alertas.
* [ ] Permisos por usuario.
* [ ] Acceso a múltiples datasets.
* [ ] Dashboards.
* [ ] Auth empresarial.
* [ ] GPU support en Ollama (CCE node pool GPU).

---

# 25. Definición de MVP terminado

El MVP estará terminado cuando podamos ejecutar:

```bash
docker compose up --build
```

y posteriormente:

```bash
curl \
  -X POST \
  http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Cuáles fueron los 5 clientes con más revenue?"
  }'
```

y recibir:

```json
{
  "thread_id": "...",
  "answer": "Los cinco clientes con mayor revenue fueron...",
  "sql": "SELECT ..."
}
```

cumpliendo además estas condiciones:

* [x] El SQL es read-only.
* [x] El SQL fue validado (SQLGlot AST).
* [x] La conexión es read-only (pool).
* [x] El usuario de PostgreSQL es read-only (`analyst_agent`).
* [x] Existe timeout (5 segundos).
* [x] Existe límite de filas (MAX_ROWS = 100).
* [x] El agente puede corregir SQL erróneo (self-healing, max 2 retries).
* [x] Los resultados provienen únicamente de datos reales.
* [x] Existe trazabilidad de la ejecución (auditoría + observabilidad).

**MVP completado.** Tenemos un **Data Analyst Agent funcional** con
pipeline SQL hardened, memoria conversacional, chatbot Chainlit,
MCP bidireccional, export CSV/Excel, charts, modelos locales (Ollama),
y deploy en Huawei Cloud CCE.

---

# 26. Histórico de commits

```text
61f28a3 ADD: Architecture diagram and initial project structure
7f73318 add: schema
1134ec0 add: etapa A — pipeline end-to-end y fixes de DB
6dab33c add: fase 16 tests (unit, integration, agent)
abfdfe9 add: etapa B memoria conversacional + Redis
1f3750b add: fase 15 auditoria (analytics_query_log)
806ef7d add: fase 17 evaluacion (dataset + metrics + reporte)
59d5001 add: fase 18 observabilidad (timings, tokens, coste por request)
b1c4648 docs: README de arranque, endpoints, tests y arquitectura
eeeb36a add: flake.nix para dev shell (Python 3.12 + PostgreSQL 16 + Redis)
1d5d4f9 add: servicio Ollama + modelos locales via LiteLLM
8a9d6df add: automatizacion ollama para tests (healthcheck, gating, makefile)
76c00bd add: fase 1 MCP - servers propios (business glossary + analytics explorer) + cliente
835bbe9 add: fase 2 MCP - agente como cliente (hibrido, preserva pipeline SQL)
88f1ab5 add: fase 3 MCP - agente como servidor (tool ask_analytics en /mcp)
8710c21 add: fase 4 chatbot Chainlit + deploy CCE
3f6ec67 add: fases 5+6 deploy MCP + tests integracion
82f3f14 docs: ARCHITECTURE.md actualizado con arquitectura completa
6157433 docs: anade diagramas Mermaid a ARCHITECTURE.md
4267d9b refactor: renombrar contenedores app-* vs litellm-* + DB/Redis propios de LiteLLM
9196d00 docs: guia de manifests CCE (deploy/cce/README.md)
```

Ramas:

* `main` — Fases 1–18 + flake.nix + README + ARCHITECTURE.
* `etapa-d` — Export CSV/Excel + charts (commit `eb56357`).
* `ollama-service` — Ollama + MCP + Chatbot + deploy CCE + renombrado contenedores.