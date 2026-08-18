# Deploy CCE — Guía de Manifests

Catálogo de los 16 manifests YAML + 1 script que componen el deploy
del Data Analyst Agent en **Huawei Cloud CCE** (Kubernetes).

Los archivos viven en `deploy/cce/` y están numerados para aplicarse
en orden:

```bash
make deploy-cce
# o manualmente:
sh deploy/cce/create-configmaps.sh
kubectl apply -f deploy/cce/
```

---

## Orden de aplicación y cadena de dependencias

```text
00-namespace
  └─► 01-secrets
        └─► 02-configmaps
              └─► 03-pvcs
                    └─► 10-postgres-agent
                    └─► 11-postgres-analytics
                    └─► 12-redis
                    └─► 13-ollama ──► 14-ollama-init (Job, espera healthy)
                                      └─► 21-litellm-db-redis
                                            └─► 15-litellm (espera ollama-init OK)
                                                  └─► 18-mcp-glossary
                                                  └─► 19-mcp-explorer
                                                  └─► 16-api (2 réplicas)
                                                        └─► 17-elb-api (EIP público :8000)
                                                        └─► 20-chatbot
                                                              └─► 22-elb-chatbot (EIP público :8001)
                                                        └─► 23-elb-litellm (EIP público :4000)
```

---

## Manifests de infraestructura (00–03)

### `00-namespace.yaml`

| Campo | Valor |
|-------|-------|
| **Kind** | `Namespace` |
| **Nombre** | `data-analyst-agent` |
| **Propósito** | Aísla todos los recursos del proyecto en un namespace propio |

Crea el namespace `data-analyst-agent` con label
`app.kubernetes.io/name: data-analyst-agent`. Todos los manifests
posteriores se despliegan dentro de este namespace.

---

### `01-secrets.yaml`

| Campo | Valor |
|-------|-------|
| **Kind** | `Secret` x4 |
| **Propósito** | Credenciales y variables sensibles |

**4 Secrets:**

| Secret | Contenido | Consumido por |
|--------|-----------|---------------|
| `app-secrets` | `MAAS_API_KEY`, `LITELLM_MASTER_KEY`, `AGENT_DATABASE_URL`, `ANALYTICS_DATABASE_URL`, `REDIS_URL`, `ANALYST_MODEL`, `LITELLM_DATABASE_URL`, `LITELLM_REDIS_URL` | `api`, `litellm`, `mcp-explorer` (via `envFrom`) |
| `app-postgres-agent-credentials` | `POSTGRES_DB=agent`, `POSTGRES_USER=agent`, `POSTGRES_PASSWORD=agent` | `app-postgres-agent` (StatefulSet) |
| `app-postgres-analytics-credentials` | `POSTGRES_DB=analytics`, `POSTGRES_USER=analytics_admin`, `POSTGRES_PASSWORD=analytics_admin` | `app-postgres-analytics` (StatefulSet) |
| `litellm-db-credentials` | `POSTGRES_DB=litellm`, `POSTGRES_USER=litellm`, `POSTGRES_PASSWORD=litellm` | `litellm-db` (StatefulSet) |

> **Notas de producción**: reemplazar los valores placeholder
> (`TU_API_KEY`, passwords en claro) por secrets reales gestionados
> via Huawei Cloud DeH (Data Encryption Service) o Sealed Secrets.

---

### `02-configmaps.yaml`

| Campo | Valor |
|-------|-------|
| **Kind** | `ConfigMap` x2 |
| **Propósito** | Configuración no sensible |

**2 ConfigMaps:**

| ConfigMap | Contenido | Consumido por |
|-----------|-----------|---------------|
| `litellm-config` | `config.yaml` embebido: 4 aliases de modelo (`analyst-smart`, `analyst-fast`, `analyst-local`, `analyst-local-fast`), `master_key` via env | `litellm` (Deployment, montado en `/app/config.yaml`) |
| `agent-db-init` | `001_audit.sql`: DDL de `analytics_query_log` (tabla + 4 índices) | `app-postgres-agent` (montado en `/docker-entrypoint-initdb.d`) |

> **Nota**: el ConfigMap `analytics-db-init` (DDL + seed de la
> analytics DB) **no** se define como YAML — se genera dinámicamente
> desde los archivos del repo via `create-configmaps.sh` (ver abajo).

---

### `03-pvcs.yaml`

| Campo | Valor |
|-------|-------|
| **Kind** | `PersistentVolumeClaim` x4 |
| **StorageClass** | `csi-disk` (EVS estándar de Huawei Cloud) |
| **Access Mode** | `ReadWriteOnce` |

**4 PVCs:**

| PVC | Tamaño | Consumido por |
|-----|--------|---------------|
| `app-agent-db-data` | 5 Gi | `app-postgres-agent` (agent DB: checkpoints + auditoría) |
| `app-analytics-db-data` | 10 Gi | `app-postgres-analytics` (analytics DB: datos de negocio) |
| `litellm-db-data` | 5 Gi | `litellm-db` (tracking de spend/logs de LiteLLM) |
| `ollama-models` | 20 Gi | `ollama` (modelos qwen2.5 descargados) |

---

## Manifests de bases de datos y cache (10–12, 21)

### `10-postgres-agent.yaml`

| Campo | Valor |
|-------|-------|
| **Kind** | `Service` + `StatefulSet` |
| **Nombre** | `app-postgres-agent` |
| **Imagen** | `postgres:16` |
| **Puerto** | 5432 |
| **PVC** | `app-agent-db-data` (5 Gi) |
| **Readiness** | `pg_isready -U agent -d agent` (5s init, 5s period) |

**Propósito**: agent DB — almacena **checkpoints** de LangGraph
(estado conversacional persistente) y la tabla de **auditoría**
`analytics_query_log`.

- Credenciales via Secret `app-postgres-agent-credentials`.
- DDL de auditoría via ConfigMap `agent-db-init` montado en
  `/docker-entrypoint-initdb.d` (se ejecuta en el primer arranque).
- Usa `StatefulSet` (no `Deployment`) para identidad de pod estable
  y volumen persistente asociado.

---

### `11-postgres-analytics.yaml`

| Campo | Valor |
|-------|-------|
| **Kind** | `Service` + `StatefulSet` |
| **Nombre** | `app-postgres-analytics` |
| **Imagen** | `postgres:16` |
| **Puerto** | 5432 |
| **PVC** | `app-analytics-db-data` (10 Gi) |
| **Readiness** | `pg_isready -U analytics_admin -d analytics` (5s init, 5s period) |

**Propósito**: analytics DB — datos de negocio (customers, orders,
products, order_items) + views + rol read-only `analyst_agent`.

- Credenciales via Secret `app-postgres-analytics-credentials`.
- DDL + seed via ConfigMap `analytics-db-init` (generado por
  `create-configmaps.sh` desde los archivos del repo).
- Usa `StatefulSet` por la misma razón que la agent DB.

---

### `12-redis.yaml`

| Campo | Valor |
|-------|-------|
| **Kind** | `Service` + `Deployment` |
| **Nombre** | `app-redis` |
| **Imagen** | `redis:7` |
| **Puerto** | 6379 |
| **Readiness** | `redis-cli ping` (3s init, 5s period) |

**Propósito**: Redis de la **aplicación** — sesiones user→thread,
caché de schema, caché de query results, rate limiting.

- Sin PVC (datos efímeros; la pérdida es tolerable).
- Usa `Deployment` (no StatefulSet) porque no necesita identidad
  estable ni volumen persistente.

---

### `21-litellm-db-redis.yaml`

| Campo | Valor |
|-------|-------|
| **Kind** | `Service` + `StatefulSet` + `Service` + `Deployment` |
| **Nombres** | `litellm-db`, `litellm-redis` |

**2 recursos en un manifest:**

| Recurso | Kind | Imagen | Puerto | PVC | Propósito |
|---------|------|--------|--------|-----|-----------|
| `litellm-db` | StatefulSet | `postgres:16` | 5432 | `litellm-db-data` (5 Gi) | Tracking de **spend**, logs y API keys de LiteLLM |
| `litellm-redis` | Deployment | `redis:7` | 6379 | — | **Caching** y rate limiting interno de LiteLLM |

**Propósito**: infraestructura **propia de LiteLLM**, separada de la
aplicación. Permite a LiteLLM persistir métricas de coste por modelo
y cachear respuestas de LLM.

- `litellm-db`: credenciales via Secret `litellm-db-credentials`;
  readiness `pg_isready -U litellm -d litellm`.
- `litellm-redis`: readiness `redis-cli ping`.
- Se aplica **antes** de `15-litellm.yaml` (LiteLLM las necesita al
  arrancar).

---

## Manifests de modelos (13–14)

### `13-ollama.yaml`

| Campo | Valor |
|-------|-------|
| **Kind** | `Service` + `Deployment` |
| **Nombre** | `ollama` |
| **Imagen** | `ollama/ollama:latest` |
| **Puerto** | 11434 |
| **PVC** | `ollama-models` (20 Gi) |
| **Readiness** | `ollama list` (10s init, 5s period, 30 retries) |

**Propósito**: servidor de **modelos locales** (qwen2.5:7b,
qwen2.5:1.5b) accesible via HTTP en `http://ollama:11434`.

- El PVC persiste los modelos descargados entre reinicios del pod
  (no se re-descargan).
- `failureThreshold: 30` da ~2.5 min de margen antes de marcar el
  pod como no listo (Ollama puede tardar en arrancar).
- Para **GPU**: añadir `nodeSelector` + `tolerations` para el node
  pool GPU de CCE y montar el dispositivo (`nvidia.com/gpu: 1`).

---

### `14-ollama-init-job.yaml`

| Campo | Valor |
|-------|-------|
| **Kind** | `Job` |
| **Nombre** | `ollama-init` |
| **Imagen** | `ollama/ollama:latest` |
| **Backoff** | 3 retries |
| **Restart** | `Never` |

**Propósito**: **descarga y verifica** los modelos de Ollama la
primera vez que se despliega el stack.

Flujo:
1. Espera a que `ollama` esté healthy (`until ollama list`).
2. `ollama pull qwen2.5:1.5b` (modelo ligero para tests, ~1 GB).
3. `ollama pull qwen2.5:7b` (modelo capaz, ~4.7 GB).
4. **Smoke test**: `ollama list | grep qwen2.5:1.5b` — si no aparece,
   exit 1 (el Job falla y reintenta).

- `backoffLimit: 3` reintenta hasta 3 veces si el pull falla.
- El `Makefile` espera a que el Job complete (`kubectl wait
  --for=condition=complete`) antes de aplicar `15-litellm.yaml`.
- En reinicios posteriores del cluster, el Job **no se re-ejecuta**
  (los modelos ya están en el PVC).

---

## Manifests de gateway y API (15–17)

### `15-litellm.yaml`

| Campo | Valor |
|-------|-------|
| **Kind** | `Service` + `Deployment` |
| **Nombre** | `litellm` |
| **Imagen** | `ghcr.io/berriai/litellm:main-latest` |
| **Puerto** | 4000 |
| **Readiness** | HTTP `GET /health/liveness` (10s init, 5s period) |

**Propósito**: **gateway de modelos** — unifica acceso a MaaS Huawei
(GLM-5.2) y Ollama (qwen2.5) bajo aliases intercambiables.

- Config via ConfigMap `litellm-config` montado en `/app/config.yaml`
  (subPath).
- Env via Secret `app-secrets` (incluye `LITELLM_DATABASE_URL` y
  `LITELLM_REDIS_URL` para tracking/caching).
- **Depende de** `ollama-init` (condition: `service_completed_successfully`)
  y de `litellm-db` + `litellm-redis` (en el Makefile se aplican antes).
- La app (`16-api`) lo consume via `LITELLM_BASE_URL=http://litellm:4000/v1`.

Aliases expuestos:
  - `analyst-smart` → `MaaS GLM-5.2`
  - `analyst-fast` → `MaaS GLM-5.2`
  - `analyst-local` → `ollama/qwen2.5:7b`
  - `analyst-local-fast` → `ollama/qwen2.5:1.5b`

---

### `16-api.yaml`

| Campo | Valor |
|-------|-------|
| **Kind** | `Service` (ClusterIP) + `Deployment` |
| **Nombre** | `api` |
| **Imagen** | `swr.<region>.myhuaweicloud.com/<org>/analyst-api:latest` |
| **Réplicas** | 2 |
| **Puerto** | 8000 |
| **Readiness** | HTTP `GET /health` (5s init, 5s period) |

**Propósito**: **FastAPI + LangGraph agent** — el núcleo del proyecto.

- 2 réplicas para alta disponibilidad (el checkpointer PostgreSQL
  permite que múltiples instancias compartan estado).
- Service `ClusterIP` (interno; el tráfico externo entra via
  `17-elb.yaml`).
- Env via Secret `app-secrets` (connection strings, API keys, modelo).
- Endpoints: `POST /chat`, `GET /export`, `GET /health`, `POST /mcp`.
- **Placeholder**: reemplazar `swr.<region>.myhuaweicloud.com/<org>`
  por la imagen real en SWR antes de aplicar.

---

### `17-elb.yaml`

| Campo | Valor |
|-------|-------|
| **Kind** | `Service` (LoadBalancer) |
| **Nombre** | `api-elb` |
| **Puerto** | 8000 → 8000 |

**Propósito**: **Elastic Load Balancer** público de Huawei Cloud CCE —
expone la API a Internet con una EIP.

Anotaciones CCE:

| Anotación | Función |
|-----------|---------|
| `kubernetes.io/elb.class: union` | Usa el ELB nativo de CCE |
| `kubernetes.io/elb.autocreate` | **Auto-crea** el ELB con EIP `5_bgp` (BGP), bandwidth 5 Mbps, nombre `analyst-api-elb` — no requiere ELB ID previo |
| `kubernetes.io/elb.health-check-flag: on` | Activa health check del ELB |
| `kubernetes.io/elb.health-check-option` | HTTP `GET /health:8000`, delay 5s, timeout 3s, 3 retries |

- Selecciona pods `app: api` (mismo selector que `16-api.yaml`).
- Tras aplicar, el EIP se obtiene con:
  ```bash
  kubectl get svc api-elb -n data-analyst-agent \
    -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
  ```

---

## Manifests de MCP (18–19)

### `18-mcp-glossary.yaml`

| Campo | Valor |
|-------|-------|
| **Kind** | `Service` + `Deployment` |
| **Nombre** | `mcp-glossary` |
| **Imagen** | `swr.cn-north-4.myhuaweicloud.com/mi-org/analyst-api:latest` |
| **Comando** | `python -m mcp_servers.servers.business_glossary` |
| **Puerto** | 8100 |
| **Readiness** | HTTP `GET /mcp` (5s init, 5s period) |

**Propósito**: **servidor MCP de glosario semántico** — expone
`data_dictionary.yaml` + business rules como **recursos MCP**
(`glossary://database`, `glossary://metrics[/{name}]`,
`glossary://tables[/{name}]`).

- Transport: **streamable HTTP** en `/mcp`.
- El agente LangGraph lo consume como cliente MCP (via
  `MCP_GLOSSARY_URL=http://mcp-glossary:8100/mcp`).
- Reusa la misma imagen de la API (incluye `mcp_servers/`).
- No requiere DB ni Redis (lee el YAML del filesystem).

---

### `19-mcp-explorer.yaml`

| Campo | Valor |
|-------|-------|
| **Kind** | `Service` + `Deployment` |
| **Nombre** | `mcp-explorer` |
| **Imagen** | `swr.cn-north-4.myhuaweicloud.com/mi-org/analyst-api:latest` |
| **Comando** | `python -m mcp_servers.servers.analytics_explorer` |
| **Puerto** | 8101 |
| **Readiness** | HTTP `GET /mcp` (5s init, 5s period) |

**Propósito**: **servidor MCP de exploración** — expone **tools MCP**
para inspeccionar la analytics DB read-only.

Tools expuestas:
  - `list_tables()` — lista tablas y views del schema `public`.
  - `describe_table(table)` — columnas, tipos y nullability.
  - `sample_table(table, n)` — n filas de muestra (max 20, timeout 5s).

- Transport: **streamable HTTP** en `/mcp`.
- Conecta a la analytics DB via `ANALYTICS_DATABASE_URL` (env from
  `app-secrets`).
- Usa pool read-only con `statement_timeout` defensivo.
- El agente lo consume via
  `MCP_EXPLORER_URL=http://mcp-explorer:8101/mcp`.

---

## Manifests de UI (20)

### `20-chatbot.yaml`

| Campo | Valor |
|-------|-------|
| **Kind** | `Service` + `Deployment` |
| **Nombre** | `chatbot` |
| **Imagen** | `swr.cn-north-4.myhuaweicloud.com/mi-org/analyst-chatbot:latest` |
| **Puerto** | 8001 |
| **Readiness** | HTTP `GET /health` (5s init, 5s period) |

**Propósito**: **chatbot Chainlit** — UI conversacional para el
usuario final.

- Env `AGENT_API_URL=http://api:8000` (apunta al Service ClusterIP
  de la API).
- Muestra: respuesta, SQL generado, chart sugerido, botones de
  export CSV/Excel.
- **Imagen separada** de la API (incluye `chainlit` + `httpx`, no
  `langchain`/`langgraph`).
- Sin Service LoadBalancer (acceso interno; para exponerlo
  públicamente, añadir un segundo ELB o un Ingress).

---

## Script auxiliar

### `create-configmaps.sh`

| Campo | Valor |
|-------|-------|
| **Tipo** | Shell script |
| **Propósito** | Genera el ConfigMap `analytics-db-init` desde los archivos SQL del repo |

**Por qué un script y no un YAML**: el ConfigMap `analytics-db-init`
contiene 5 archivos SQL del repositorio (schema, indexes, views,
agent_role, seed) que totalizan ~400 líneas. En lugar de duplicarlos
embebidos en un YAML, el script los lee del repo y los inyecta:

```bash
kubectl create configmap analytics-db-init \
  --from-file=001_schema.sql=database/analytics/ddl/001_schema.sql \
  --from-file=002_indexes.sql=database/analytics/ddl/002_indexes.sql \
  ...
```

- Se ejecuta **antes** de `kubectl apply -f deploy/cce/` (lo hace
  el target `make deploy-cce`).
- Usa `--dry-run=client -o yaml | kubectl apply -f -` (idempotente:
  crea o actualiza el ConfigMap si ya existe).
- Los SQL se montan en `/docker-entrypoint-initdb.d` del
  `app-postgres-analytics` StatefulSet (se ejecutan en el primer
  arranque del pod).

---

## Tabla resumen

| # | Archivo | Kind(s) | Recursos | Puerto(s) |
|---|---------|---------|----------|-----------|
| 00 | `00-namespace.yaml` | Namespace | `data-analyst-agent` | — |
| 01 | `01-secrets.yaml` | Secret x4 | app-secrets, pg-agent-creds, pg-analytics-creds, litellm-db-creds | — |
| 02 | `02-configmaps.yaml` | ConfigMap x2 | litellm-config, agent-db-init | — |
| 03 | `03-pvcs.yaml` | PVC x4 | app-agent-db (5Gi), app-analytics-db (10Gi), litellm-db (5Gi), ollama-models (20Gi) | — |
| 10 | `10-postgres-agent.yaml` | Service + StatefulSet | `app-postgres-agent` | 5432 |
| 11 | `11-postgres-analytics.yaml` | Service + StatefulSet | `app-postgres-analytics` | 5432 |
| 12 | `12-redis.yaml` | Service + Deployment | `app-redis` | 6379 |
| 13 | `13-ollama.yaml` | Service + Deployment | `ollama` | 11434 |
| 14 | `14-ollama-init-job.yaml` | Job | `ollama-init` | — |
| 15 | `15-litellm.yaml` | Service + Deployment | `litellm` | 4000 |
| 16 | `16-api.yaml` | Service (ClusterIP) + Deployment (x2) | `api` | 8000 |
| 17 | `17-elb.yaml` | Service (LoadBalancer) | `api-elb` | 8000 |
| 18 | `18-mcp-glossary.yaml` | Service + Deployment | `mcp-glossary` | 8100 |
| 19 | `19-mcp-explorer.yaml` | Service + Deployment | `mcp-explorer` | 8101 |
| 20 | `20-chatbot.yaml` | Service + Deployment | `chatbot` | 8001 |
| 21 | `21-litellm-db-redis.yaml` | Service + StatefulSet + Service + Deployment | `litellm-db`, `litellm-redis` | 5432, 6379 |
| 22 | `22-elb-chatbot.yaml` | Service (LoadBalancer) | `chatbot-elb` | 8001 |
| 23 | `23-elb-litellm.yaml` | Service (LoadBalancer) | `litellm-elb` | 4000 |
| — | `create-configmaps.sh` | Script | genera ConfigMap `analytics-db-init` | — |

**Total**: 18 YAML + 1 script = **30 recursos Kubernetes** (namespaces,
secrets, configmaps, PVCs, services, deployments, statefulsets, jobs).

---

## Placeholders a reemplazar antes de aplicar

| Placeholder | Archivo(s) | Reemplazar por |
|-------------|-----------|----------------|
| `MAAS_API_KEY` | `01-secrets.yaml` | API key real de Huawei Cloud MaaS (o usar `analyst-local-fast` sin key) |
| `sk-local-secret` | `01-secrets.yaml` | Master key real de LiteLLM |
| Passwords en claro | `01-secrets.yaml` | Passwords reales o secrets gestionados |
| `swr.<region>.myhuaweicloud.com/<org>/analyst-api:latest` | `16-api.yaml` | Imagen real en SWR |
| `swr.cn-north-4.myhuaweicloud.com/mi-org/analyst-api:latest` | `18-mcp-glossary.yaml`, `19-mcp-explorer.yaml` | Imagen real en SWR |
| `swr.cn-north-4.myhuaweicloud.com/mi-org/analyst-chatbot:latest` | `20-chatbot.yaml` | Imagen real en SWR |

---

## Verificación post-deploy

```bash
# Pods
kubectl get pods -n data-analyst-agent

# Services + EIP
kubectl get svc -n data-analyst-agent

# Health check via port-forward
kubectl port-forward svc/api -n data-analyst-agent 8000:8000
curl http://localhost:8000/health

# Probar /chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "¿Cuánto revenue hubo en julio?"}'

# Logs del agente
kubectl logs -f deployment/api -n data-analyst-agent

# Logs del job de init de ollama
kubectl logs job/ollama-init -n data-analyst-agent

# Estado del checkpointer (agent DB)
kubectl exec -it statefulset/app-postgres-agent -n data-analyst-agent -- \
  psql -U agent -d agent -c "\dt"
```