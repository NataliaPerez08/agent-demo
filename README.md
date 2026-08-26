# Data Analyst Agent

Agente que recibe preguntas en lenguaje natural sobre datos de ventas,
las convierte en SQL seguro, consulta la base analítica y responde
manteniendo contexto conversacional. Incluye **chatbot Chainlit**,
integración **MCP bidireccional** (cliente + servidor) y export
CSV/Excel + sugerencia de charts.

- **API**: FastAPI + LangGraph (grafo híbrido SQL | MCP)
- **Chatbot**: Chainlit (:8001) con streaming, SQL display y export
- **MCP**: bidireccional — consume 4 servers MCP y expone `ask_analytics`
- **Modelos**: LiteLLM (gateway a MaaS Huawei GLM-5.2 + Ollama local)
- **Datos analíticos**: PostgreSQL (rol read-only `analyst_agent`)
- **Memoria / checkpoints**: PostgreSQL (agent DB)
- **Sesiones / caché / rate limit**: Redis
- **Validación SQL**: SQLGlot (AST + whitelist de esquemas + timeout)

---

## Arquitectura

```text
[Usuario]
    │
    ▼
[Chainlit :8001] ──HTTP──► [/chat FastAPI :8000] ──► [LangGraph agent]
                                                        │
                                              classify_question
                                                  │
                                    ┌─────────────┴─────────────┐
                                    ▼                           ▼
                            Pipeline SQL                 MCP loop
                            (determinista)            (agent_with_tools
                            validate AST                ↔ mcp_tools)
                            read-only                       │
                            timeout                         │
                            auditoría                       ▼
                                    │                  answer (tools)
                                    ▼
                           answer + SQL + chart
                                    │
                          [/mcp endpoint]
                           expone ask_analytics
                           para Claude Desktop
                           y otros clientes MCP
```

Servidores MCP consumidos por el agente:

| Server | Tipo | Puerto | Descripción |
|--------|------|--------|-------------|
| `business-glossary` | Resources | 8100 | `data_dictionary.yaml` + business rules como recursos MCP |
| `analytics-explorer` | Tools | 8101 | `list_tables()`, `describe_table()`, `sample_table()` |
| `filesystem` | Tools | 8102 | Lectura de archivos/docs locales (estándar) |
| `websearch` | Tools | 8103 | Búsqueda web para datos externos (estándar) |

Pipeline SQL del agente (preservado, determinista):

```text
question → retrieve_schema → classify → generate_sql → validate_sql
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
- `MAAS_API_KEY` válida **o** `ANALYST_MODEL=analyst-local-fast` (Ollama, sin API key)

---

## Puesta en marcha

1. Copiar variables y setear la API key de MaaS (o usar modelo local):

   ```bash
   cp .env.example .env
   # editar .env:
   #   MAAS_API_KEY=sk-...           (o dejar TU_API_KEY si usas Ollama)
   #   ANALYST_MODEL=analyst-local-fast  (para modelo local sin coste)
   ```

2. Levantar el stack:

   ```bash
   docker compose up --build
   ```

   Servicios levantados (10):

   | Servicio | Puerto | Descripción |
   |----------|--------|-------------|
   | `api` | 8000 | FastAPI + LangGraph agent |
   | `chatbot` | 8001 | Chainlit UI |
   | `litellm` | 4000 | Gateway de modelos |
   | `ollama` | 11434 | Modelos locales |
   | `ollama-init` | — | Job: descarga modelos (1ª vez) |
   | `postgres` | 5432 | Agent DB (checkpoints + auditoría) |
   | `analytics` | 5433 | Analytics DB (datos + rol read-only) |
   | `redis` | 6379 | Sesiones + caché + rate limit |
   | `mcp-glossary` | 8100 | Server MCP: glosario semántico |
   | `mcp-explorer` | 8101 | Server MCP: exploración de tablas |

3. Health check:

   ```bash
   curl http://localhost:8000/health
   # {"status":"ok"}
   ```

4. Preguntar vía API:

   ```bash
   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"question": "¿Cuáles fueron los 5 clientes con más revenue?"}'
   ```

5. **O usar el chatbot** en `http://localhost:8001`:

   UI de Chainlit con streaming, muestra respuesta + SQL + chart sugerido,
   y botones para exportar CSV/Excel.

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

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Status del servicio |
| POST | `/chat` | Pregunta al agente (answer + sql + chart) |
| GET | `/export` | Descarga último resultado en CSV o XLSX |
| POST/GET | `/mcp` | Servidor MCP (streamable HTTP) — tool `ask_analytics` |

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

### Charts

`/chat` devuelve `chart`: sugerencia de visualización heurística derivada
de los resultados (sin LLM extra). Tipos: `line` (temporal), `bar`
(categoría + métrica), `pie` (≤6 filas). Columnas `id`/`*_id` excluidas.
Si no encaja ningún patrón, `chart` es `null`.

### MCP (`/mcp`)

El agente expone la tool `ask_analytics(question)` vía MCP streamable HTTP.
Clientes MCP como Claude Desktop pueden consumirla:

```
URL: http://<host>:8000/mcp
Transport: streamable-http
Tool: ask_analytics(question: str) -> str
```

---

## MCP: integración bidireccional

El agente es **cliente y servidor MCP** simultáneamente.

### Agente como cliente (consume tools MCP)

El grafo LangGraph es **híbrido**: tras recuperar el schema, un
clasificador heurístico (`classify_question`) decide:

- **`"sql"`** → pipeline SQL determinista (preservado 100%: validación AST,
  read-only, timeout, auditoría)
- **`"mcp"`** → loop reactivo con `ToolNode` (el LLM decide qué tools MCP
  llamar)

Si no hay servidores MCP configurados, el agente arranca en modo
pipeline-only (backward compatible).

### Agente como servidor (expone `ask_analytics`)

El endpoint `/mcp` monta un `FastMCP` server con la tool
`ask_analytics(question: str) -> str` que invoca el grafo internamente.
Permite que clientes MCP externos usen el data analyst agent como una
capability más.

### Servidores MCP propios

```text
mcp_servers/
├── servers/
│   ├── business_glossary.py    Resources: glossary://database, metrics, tables
│   └── analytics_explorer.py   Tools: list_tables, describe_table, sample_table
└── client.py                   MultiServerMCPClient (4 servers, fail-open)
```

---

## Estructura del repositorio

```text
app/
├── main.py                     FastAPI + lifespan (DB + checkpointer + MCP)
├── config.py                   Settings (env, ANALYST_MODEL)
├── agent/
│   ├── state.py                AnalystState (TypedDict: question_type, messages)
│   ├── routing.py              classify_question + routing SQL|MCP
│   ├── mcp_tools.py            agent_with_tools + mcp_answer (loop reactivo)
│   └── graph.py                StateGraph híbrido (build_graph(checkpointer, mcp_tools))
├── nodes/
│   ├── schema.py               retrieve_schema (+ caché Redis + relaciones FK)
│   ├── generate_sql.py         LLM → SQL
│   ├── validate_sql.py         SQLGlot AST validator (whitelist + funciones)
│   ├── execute_sql.py          pool async + timeout + MAX_ROWS + caché query
│   ├── fix_sql.py              self-healing (max 2 retries)
│   ├── analyze.py              análisis de resultados
│   ├── answer.py               respuesta final
│   └── failure.py              nodo terminal
├── api/
│   ├── routes.py               POST /chat + GET /export
│   ├── schemas.py              ChatRequest/Response + ChartConfig
│   └── mcp_server.py           FastMCP server: tool ask_analytics (/mcp)
├── infrastructure/
│   ├── postgres.py             pools + AsyncPostgresSaver (checkpointer)
│   ├── redis.py               caché/sesión/rate-limit (fail-open)
│   ├── llm.py                 get_llm + ainvoke_with_usage (tokens)
│   ├── audit.py                log_query → analytics_query_log
│   └── observability.py        Observation (contextvar), timed, reporte
├── services/
│   ├── export.py               rows → CSV / XLSX
│   └── charts.py               suggest_chart (line/bar/pie)
└── eval/
    ├── metrics.py              métricas por dimensión
    └── evaluator.py           run_dataset + summarize + reporte

mcp_servers/                    Servidores MCP propios + cliente
├── servers/
│   ├── business_glossary.py    Resources MCP (data_dictionary)
│   └── analytics_explorer.py   Tools MCP (list/describe/sample)
└── client.py                   MultiServerMTPClient (fail-open)

chatbot/                        UI Chainlit
├── app.py                      Chat con SQL display + chart + export
├── agent_client.py             Cliente HTTP async para /chat + /export
├── Dockerfile                  Imagen separada
└── requirements.txt            chainlit + httpx

database/
├── analytics/                  datos de negocio (rol read-only)
│   ├── ddl/  (schema, indexes, views, agent_role)
│   ├── dml/  (seed)
│   └── model/ (data_dictionary.yaml, erd.md)
└── agent/                      checkpoints + auditoría
    └── ddl/  (001_audit.sql)

deploy/cce/                     Manifests Kubernetes (Huawei Cloud CCE)
├── 00-namespace … 17-elb       Infra + datos + API + ELB
├── 18-mcp-glossary             Deployment + Service (:8100)
├── 19-mcp-explorer             Deployment + Service (:8101)
├── 20-chatbot                  Deployment + Service (:8001)
└── create-configmaps.sh        Genera ConfigMap SQL analytics

eval/dataset.yaml               dataset de evaluación (6 casos)
litellm/config.yaml             modelos (MaaS + Ollama)
Makefile                        targets: up/down/test/image/deploy-cce/mcp/chatbot
flake.nix                       dev shell (Nix)
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

## Makefile

```bash
make help          # lista todos los targets

# Stack
make up            # docker compose up --build
make down          # detiene el stack

# Ollama
make ollama-up     # levanta ollama + descarga modelos
make ollama-logs   # logs

# MCP
make mcp-up        # levanta glossary + explorer
make mcp-logs      # logs

# Chatbot
make chatbot-up    # levanta Chainlit
make chatbot-logs  # logs

# Tests
make test          # pytest completo
make test-unit     # solo unitarios
make test-local    # pytest con modelo local (RUN_AGENT=1)
make test-local-up # levanta ollama + DBs, corre tests, baja al finish

# Imagen Docker (SWR Huawei Cloud)
make image-build   # construye imagen
make image-push    # login SWR + push
make image         # build + push

# Deploy CCE
make deploy-cce    # aplica manifests en orden + espera rollout
```

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
$env:RUN_AGENT="1"           # PowerShell  (export RUN_AGENT=1 en *nix)
$env:MAAS_API_KEY="sk-..."
py -m pytest tests -q
```

| Suite | Requiere | Marker |
|-------|----------|--------|
| unit | nada | — |
| integration | analytics/agent DB | `integration` |
| agent (e2e/eval) | DB + LLM + `RUN_AGENT=1` | `agent` |

Unitarios cubren (76 tests): validador SQL (18 casos), observabilidad
(timings, tokens, coste), export CSV/XLSX, sugerencia de charts,
clasificador SQL|MCP (21 casos), servers MCP (glossary resources +
explorer tools con pool mockeado), cliente MCP, servidor MCP export
(`ask_analytics`), cliente HTTP del chatbot.

### Tests con modelo local (Ollama, sin API key)

```bash
# Linux/macOS
make test-local-up

# Windows
.\scripts\test-local.ps1 -Up -Down
```

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

| Variable | Descripción |
|----------|-------------|
| `MAAS_API_KEY` | API key de Huawei Cloud MaaS (consumo vía LiteLLM) |
| `LITELLM_MASTER_KEY` | Master key del gateway LiteLLM |
| `LITELLM_BASE_URL` | URL del gateway (interno en compose) |
| `AGENT_DATABASE_URL` | PostgreSQL del agente (checkpoints+audit) |
| `ANALYTICS_DATABASE_URL` | PostgreSQL analítica (rol read-only) |
| `REDIS_URL` | URL de Redis |
| `ANALYST_MODEL` | Alias de modelo (`analyst-smart` por defecto; ver Ollama) |
| `MCP_GLOSSARY_URL` | URL del server MCP glosario (`/mcp`) |
| `MCP_EXPLORER_URL` | URL del server MCP explorer (`/mcp`) |
| `MCP_FILESYSTEM_URL` | URL del server MCP filesystem (opcional) |
| `MCP_WEBSEARCH_URL` | URL del server MCP websearch (opcional) |

---

## Modelos locales con Ollama (sin API key, sin coste)

El stack incluye un servicio **Ollama** que LiteLLM expone como modelos
alternativos. Para usarlos, define en `.env`:

```env
ANALYST_MODEL=analyst-local        # qwen2.5:7b  (capaz)
# o
ANALYST_MODEL=analyst-local-fast   # qwen2.5:1.5b (ligero, recomendado para tests)
```

`docker compose up --build` levanta además `ollama-init`, que descarga los
modelos la **primera vez** (puede tardar varios minutos según conexión).
Cadena robusta: healthcheck → pull → smoke → litellm → api (cero 404s).

> Nota: en CPU los modelos grandes son lentos. Para GPU, monta el dispositivo
> en el servicio `ollama` del compose.

Aliases disponibles (definidos en `litellm/config.yaml`):

| Alias | Backend | Notas |
|-------|---------|-------|
| `analyst-smart` | MaaS GLM-5.2 | default, requiere API key |
| `analyst-fast` | MaaS GLM-5.2 | rápido, requiere API key |
| `analyst-local` | Ollama qwen2.5:7b | local, sin coste |
| `analyst-local-fast` | Ollama qwen2.5:1.5b | local, ligero |

---

## Deploy automatizado (CI/CD + Terraform)

El proyecto incluye despliegue **100% automatizado** vía GitHub Actions +
Terraform. Los manifiestos K8s en `deploy/cce/*.yaml` son la **única fuente
de verdad**: Terraform los lee con `templatefile()` + `yamldecode()` y los
aplica vía `kubernetes_manifest`.

### Pipeline GitHub Actions (`.github/workflows/deploy.yml`)

| Evento | Jobs |
|--------|------|
| PR | test (ruff + pytest unit) → terraform plan |
| Push a `main` | test → build/push SWR (tags `latest`+SHA) → mirror imágenes → terraform apply → refresh (EIPs reales) → smoke `/health` |
| `workflow_dispatch` | igual que push a `main` |

`concurrency: deploy-${{ github.ref }}` evita applies paralelos.

### Secrets y variables de GitHub

| Tipo | Nombre | Descripción |
|------|--------|-------------|
| Secret | `HW_ACCESS_KEY` | Access Key de Huawei Cloud (IAM) |
| Secret | `HW_SECRET_KEY` | Secret Access Key de Huawei Cloud |
| Secret | `MAAS_API_KEY` | API key de MaaS (vacío si usa Ollama) |
| Secret | `LITELLM_MASTER_KEY` | Master key de LiteLLM |
| Variable | `TF_BUCKET` | Bucket OBS para el state de Terraform |

> El login a SWR se deriva de `HW_ACCESS_KEY`/`HW_SECRET_KEY` (fórmula
> HMAC-SHA256 oficial de Huawei) — no requiere secretos adicionales.

### Terraform

```text
terraform/
├── main.tf              Providers (huaweicloud + kubernetes con certs del CCE)
├── versions.tf          required_providers + backend S3 (OBS)
├── variables.tf         todas las variables (sensibles + imágenes)
├── locals.tf            passwords aleatorios + vars para templatefile
├── network.tf           VPC + subnet + security group
├── cce.tf               CCE cluster + node pool + EIP master
├── swr.tf               SWR org + repos (analyst-api, analyst-chatbot)
├── elb.tf               (ELBs auto-creados por CCE via annotations)
├── k8s-manifests.tf     kubernetes_manifest leyendo deploy/cce/*.yaml
├── k8s-secrets.tf       Secrets nativos desde variables sensibles
├── k8s-configmaps.tf    ConfigMaps SQL generados desde database/
├── smoke.tf             Smoke test post-apply (kubectl + curl /health)
├── outputs.tf           EIPs reales + endpoints
├── backend.hcl.example  Config del backend OBS (copiar a backend.hcl)
└── terraform.tfvars.example
```

### Deploy local (un comando)

```bash
# 1. Configurar credenciales
export HW_ACCESS_KEY=...
export HW_SECRET_KEY=...
export TF_BUCKET=mi-bucket-tfstate

# 2. Deploy end-to-end
make deploy        # build + push + mirror + terraform apply
```

### Migración (si el cluster CCE ya existe)

Importar los recursos existentes antes del primer `terraform apply`:

```bash
cd terraform
terraform import huaweicloud_cce_cluster.agent <cluster-id>
terraform import huaweicloud_vpc.agent <vpc-id>
terraform import huaweicloud_vpc_subnet.agent <subnet-id>
terraform import huaweicloud_swr_organization.agent <org-name>
terraform import huaweicloud_swr_repository.api <org>/<repo>
terraform import huaweicloud_swr_repository.chatbot <org>/<repo>
```

---

## Deploy en Huawei Cloud CCE (manual / legacy)

Manifests en `deploy/cce/` (16 YAML + 1 script). Los manifiestos usan
placeholders (`${api_image}`, `${namespace}`, etc.) que Terraform resuelve
automáticamente. Para deploy manual con kubectl, usar `make deploy-cce`
(requiere `envsubst`).

Para la guía detallada de cada manifest, ver `deploy/cce/README.md`.

### Requisitos previos

- Huawei Cloud CLI (`hcloud`) o acceso a la consola web
- `kubectl` configurado contra el cluster CCE
- Docker para construir y subir imágenes
- SWR (SoftWare Repository) accessible

### Paso 1 — Configurar variables

```bash
cd deploy/cce
cp .env.example .env     # si existe
# editar .env / 01-secrets.yaml:
#   MAAS_API_KEY         (o usar analyst-local-fast sin key)
#   SWR_REGION, SWR_ORG  (región y organización de SWR)
```

Reemplazar en los manifests:

| Placeholder | Archivo(s) | Reemplazar por |
|-------------|-----------|----------------|
| `TU_API_KEY` | `01-secrets.yaml` | API key real o dejar para Ollama local |
| `sk-local-secret` | `01-secrets.yaml` | Master key real de LiteLLM |
| Passwords en claro | `01-secrets.yaml` | Passwords reales o secrets gestionados |
| `swr.<region>.../analyst-api:latest` | `16-api`, `18-*`, `19-*` | Imagen real en SWR |
| `swr.<region>.../analyst-chatbot:latest` | `20-chatbot.yaml` | Imagen real en SWR |

### Paso 2 — Construir y publicar imagen

```bash
# Login en SWR
docker login -u <org> swr.<region>.myhuaweicloud.com

# Build + push (una imagen para api, mcp-glossary, mcp-explorer)
make image-build    # construye analyst-api:latest
make image-push     # push a SWR
```

### Paso 3 — Desplegar en CCE

```bash
make deploy-cce
```

Esto ejecuta en orden:
1. `create-configmaps.sh` — genera ConfigMap `analytics-db-init`
2. Namespace → Secrets → ConfigMaps → PVCs
3. Postgres (agent + analytics) → Redis → Ollama
4. `ollama-init` Job (descarga modelos, ~5 min primera vez)
5. LiteLLM DB/Redis → LiteLLM
6. MCP servers → API (2 réplicas) → ELB → Chatbot

Cadena de dependencias:

```text
ollama healthy → ollama-init complete → litellm start → api start → chatbot start
```

### Paso 4 — Verificar

```bash
# Pods
kubectl get pods -n data-analyst-agent

# Services + EIP del ELB
kubectl get svc -n data-analyst-agent

# Health check
kubectl port-forward svc/api -n data-analyst-agent 8000:8000
curl http://localhost:8000/health
# → {"status":"ok"}

# EIP público del ELB
kubectl get svc api-elb -n data-analyst-agent \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# Probar /chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "¿Cuánto revenue hubo en julio?"}'

# Logs
kubectl logs -f deployment/api -n data-analyst-agent
kubectl logs job/ollama-init -n data-analyst-agent
```

### Paso 5 — Usar

- **API**: `http://<EIP-API>:8000` (vía ELB público)
- **Chatbot**: `http://<EIP-Chatbot>:8001` (vía ELB público)
- **LiteLLM**: `http://<EIP-LiteLLM>:4000` (vía ELB público)
- **MCP**: `http://<EIP-API>:8000/mcp` (Claude Desktop o clientes MCP)

### Arquitectura CCE

```text
Internet
    │
    ├──► ELB api-elb (:8000) ──► api (x2 réplicas)
    ├──► ELB chatbot-elb (:8001) ──► chatbot
    └──► ELB litellm-elb (:4000) ──► litellm
                                      │
                            ┌─────────┼─────────┐
                            ▼         ▼         ▼
                      litellm-db  litellm-redis  ollama
                                                    │
                                              ollama-init (Job)
```

### Recursos desplegados

| # | Archivo | Kind(s) | Puerto(s) |
|---|---------|---------|-----------|
| 00 | `00-namespace.yaml` | Namespace | — |
| 01 | `01-secrets.yaml` | Secret x4 | — |
| 02 | `02-configmaps.yaml` | ConfigMap x2 | — |
| 03 | `03-pvcs.yaml` | PVC x4 | — |
| 10 | `10-postgres-agent.yaml` | Service + StatefulSet | 5432 |
| 11 | `11-postgres-analytics.yaml` | Service + StatefulSet | 5432 |
| 12 | `12-redis.yaml` | Service + Deployment | 6379 |
| 13 | `13-ollama.yaml` | Service + Deployment | 11434 |
| 14 | `14-ollama-init-job.yaml` | Job | — |
| 15 | `15-litellm.yaml` | Service + Deployment | 4000 |
| 16 | `16-api.yaml` | Service + Deployment (x2) | 8000 |
| 17 | `17-elb.yaml` | Service (LoadBalancer) | 8000 |
| 18 | `18-mcp-glossary.yaml` | Service + Deployment | 8100 |
| 19 | `19-mcp-explorer.yaml` | Service + Deployment | 8101 |
| 20 | `20-chatbot.yaml` | Service + Deployment | 8001 |
| 21 | `21-litellm-db-redis.yaml` | Service + StatefulSet + Deployment | 5432, 6379 |
| 22 | `22-elb-chatbot.yaml` | Service (LoadBalancer) | 8001 |
| 23 | `23-elb-litellm.yaml` | Service (LoadBalancer) | 4000 |

### Notas de producción

- **Secrets**: usar Huawei Cloud DeH o Sealed Secrets en vez de
  passwords en claro.
- **GPU**: añadir `nodeSelector` + `tolerations` al deployment de
  Ollama para el node pool GPU de CCE.
- **Modelo**: por defecto usa Ollama local (`analyst-local-fast`).
  Para MaaS, reemplazar `MAAS_API_KEY` en `app-secrets`.

---

## Nix (dev shell alternativo)

```bash
nix develop
# Python 3.12 + PostgreSQL 16 + Redis + venv con requirements
```

---

## Estado del proyecto

- **Fases 1–18** completadas (MVP + conversacional + confiabilidad).
- **Etapa D**: export CSV/Excel + charts ✅.
- **MCP + Chatbot**: servers propios, agente cliente/servidor MCP,
  Chainlit ✅.
- **Deploy**: CI/CD automatizado (GitHub Actions + Terraform) ✅.
- **CCE**: manifests Kubernetes para Huawei Cloud CCE ✅.

Ver `action_plan.md` y `git log` para el histórico por etapa.