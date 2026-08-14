# Plan de Acción — Data Analyst Agent

## 1. Objetivo

Construir un **Data Analyst Agent** capaz de recibir preguntas en lenguaje natural, convertirlas en SQL seguro, consultar datos empresariales, analizar resultados y responder manteniendo contexto conversacional.

Arquitectura base:

```text
Usuario
   │
   ▼
FastAPI + LangGraph
   │
   ├────► LiteLLM
   │        └─ modelos
   │
   ├────► PostgreSQL
   │        ├─ datos analíticos
   │        ├─ historial
   │        └─ checkpoints
   │
   └────► Redis
            ├─ sesiones
            └─ cache
```

---

# 2. Estado actual

## Arquitectura definida

* [x] FastAPI como API.
* [x] LangChain / LangGraph como orquestador.
* [x] LiteLLM como gateway de modelos.
* [x] PostgreSQL para persistencia y datos analíticos.
* [x] Redis para sesiones y cache.
* [x] Separación entre base del agente y base analítica.
* [x] Usuario PostgreSQL read-only para el agente.

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
* [x] DML / seed de desarrollo.
* [x] `data_dictionary.yaml`.
* [x] ERD.
* [x] Índices.
* [x] Role read-only.

## Pipeline diseñado

```text
question
   │
   ▼
retrieve_schema
   │
   ▼
generate_sql
   │
   ▼
validate_sql
   │
   ▼
execute_sql
   │
   ▼
analyze_results
   │
   ▼
generate_answer
```

También se definió recuperación automática:

```text
SQL inválido / error DB
        │
        ▼
     fix_sql
        │
        ▼
   validate_sql
```

Máximo sugerido:

```text
2 retries
```

---

# 3. Estructura objetivo del repositorio

```text
data-analyst-agent/
├── app/
│   ├── main.py
│   ├── config.py
│   │
│   ├── agent/
│   │   ├── graph.py
│   │   ├── state.py
│   │   └── routing.py
│   │
│   ├── nodes/
│   │   ├── schema.py
│   │   ├── generate_sql.py
│   │   ├── validate_sql.py
│   │   ├── execute_sql.py
│   │   ├── fix_sql.py
│   │   ├── analyze.py
│   │   ├── answer.py
│   │   └── failure.py
│   │
│   └── infrastructure/
│       ├── postgres.py
│       ├── redis.py
│       └── llm.py
│
├── database/
│   ├── analytics/
│   │   ├── ddl/
│   │   │   ├── 001_schema.sql
│   │   │   ├── 002_indexes.sql
│   │   │   ├── 003_views.sql
│   │   │   └── 004_agent_role.sql
│   │   │
│   │   ├── dml/
│   │   │   └── 001_seed.sql
│   │   │
│   │   └── model/
│   │       ├── data_dictionary.yaml
│   │       └── erd.md
│   │
│   └── agent/
│       └── ddl/
│
├── tests/
│   ├── unit/
│   └── integration/
│
├── litellm/
│   └── config.yaml
│
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

# 4. Fase 1 — Fundaciones

## Infraestructura

* [ ] Crear físicamente el repositorio.
* [ ] Agregar `Dockerfile`.
* [ ] Agregar `docker-compose.yml`.
* [ ] Agregar `.env.example`.
* [ ] Configurar FastAPI.
* [ ] Configurar LiteLLM.
* [ ] Configurar PostgreSQL Agent DB.
* [ ] Configurar PostgreSQL Analytics DB.
* [ ] Configurar Redis.
* [ ] Crear endpoint `/health`.

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

* [ ] Crear `001_schema.sql`.
* [ ] Crear `002_indexes.sql`.
* [ ] Crear `003_views.sql`.
* [ ] Crear `004_agent_role.sql`.

## Seed

* [ ] Completar `001_seed.sql`.
* [ ] Verificar relaciones.
* [ ] Verificar fechas.
* [ ] Verificar estados.
* [ ] Garantizar consistencia entre órdenes y líneas.

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

* [ ] Revenue.
* [ ] Total orders.
* [ ] Average order value.
* [ ] Active customers.
* [ ] New customers.
* [ ] Units sold.
* [ ] Product revenue.

Definir dimensiones:

* [ ] País.
* [ ] Ciudad.
* [ ] Segmento.
* [ ] Producto.
* [ ] Categoría.
* [ ] Fecha.

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

* [ ] Obtener tablas.
* [ ] Obtener columnas.
* [ ] Obtener tipos.
* [ ] Obtener primary keys.
* [ ] Obtener foreign keys.
* [ ] Obtener views.
* [ ] Cargar `data_dictionary.yaml`.
* [ ] Combinar estructura y semántica.
* [ ] Generar `schema_context`.
* [ ] Cachear resultado en Redis.

Flujo:

```text
information_schema
        │
        ├────► tablas
        ├────► columnas
        ├────► tipos
        └────► relaciones

data_dictionary.yaml
        │
        └────► significado empresarial

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

* [ ] Recibir pregunta.
* [ ] Recibir esquema.
* [ ] Recibir reglas de negocio.
* [ ] Generar PostgreSQL.
* [ ] Solo permitir queries de lectura.
* [ ] Evitar `SELECT *`.
* [ ] Aplicar `LIMIT`.
* [ ] Soportar CTEs.
* [ ] Manejar preguntas imposibles.

Respuesta ideal estructurada:

```json
{
  "can_answer": true,
  "sql": "SELECT ...",
  "reason": null
}
```

En vez de depender únicamente de texto plano.

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

* [ ] `INSERT`
* [ ] `UPDATE`
* [ ] `DELETE`
* [ ] `DROP`
* [ ] `ALTER`
* [ ] `CREATE`
* [ ] `TRUNCATE`
* [ ] `COPY`
* [ ] `CALL`
* [ ] `GRANT`
* [ ] `REVOKE`

## Adicionalmente

* [ ] Solo una sentencia.
* [ ] Bloquear funciones peligrosas.
* [ ] Bloquear acceso a `pg_catalog`.
* [ ] Bloquear acceso a `information_schema`.
* [ ] Whitelist de tablas.
* [ ] Whitelist de views.
* [ ] Máximo de filas.
* [ ] Validar que exista `SELECT`.

Capas de seguridad:

```text
LLM
 │
 ▼
SQL AST validator
 │
 ▼
table whitelist
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

* [ ] Pool async.
* [ ] Usuario `analyst_agent`.
* [ ] Conexión read-only.
* [ ] `statement_timeout`.
* [ ] Máximo de filas.
* [ ] Resultados como diccionarios.
* [ ] Capturar duración.
* [ ] Capturar row count.
* [ ] Capturar truncamiento.
* [ ] Capturar errores.

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

* [ ] Máximo 2 retries.
* [ ] Revalidar después de cada corrección.
* [ ] No ejecutar directamente después del fix.
* [ ] Registrar intentos.
* [ ] Evitar loops infinitos.

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

* [ ] Identificar tendencias.
* [ ] Encontrar rankings.
* [ ] Calcular diferencias.
* [ ] Detectar anomalías.
* [ ] Evitar inventar datos.
* [ ] Identificar muestras pequeñas.
* [ ] Separar hechos de inferencias.
* [ ] Evitar afirmar causalidad sin evidencia.

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

Estado sugerido:

```text
question
user_id
thread_id

schema_context

generated_sql

sql_valid
validation_error

query_result
result_truncated
execution_error

analysis
answer

retry_count
```

Graph:

```text
START
  │
  ▼
retrieve_schema
  │
  ▼
generate_sql
  │
  ▼
validate_sql
  │
  ├────────────── inválido ──────┐
  │                              │
  ▼                              ▼
execute_sql                    fix_sql
  │                              │
  ├──── error ────────────────────┘
  │
  ▼
analyze_results
  │
  ▼
generate_answer
  │
  ▼
END
```

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
  "sql": "SELECT ..."
}
```

Durante desarrollo:

```text
include_sql = true
```

Para producción:

```text
include_sql = configurable
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

* [ ] `langgraph-checkpoint-postgres`.
* [ ] `AsyncPostgresSaver`.
* [ ] Setup de tablas.
* [ ] `thread_id`.
* [ ] Recuperación de conversación.
* [ ] Follow-ups.
* [ ] Persistencia entre reinicios.

---

# 17. Fase 14 — Redis

Usos:

```text
session:{user_id}
schema:analytics
query:{hash}
lock:{thread_id}
```

Implementar:

* [ ] Session → thread mapping.
* [ ] Schema cache.
* [ ] Query cache.
* [ ] TTLs.
* [ ] Rate limiting.
* [ ] Locks.

Principio:

```text
PostgreSQL = durable
Redis      = ephemeral
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
user_id
thread_id

question
generated_sql

successful
execution_ms
row_count

model
retry_count

created_at
```

Registrar:

* [ ] Query original.
* [ ] SQL generado.
* [ ] Intentos.
* [ ] Errores.
* [ ] Latencia.
* [ ] Modelo.
* [ ] Row count.

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

* [ ] SELECT.
* [ ] WITH.
* [ ] DELETE.
* [ ] UPDATE.
* [ ] DROP.
* [ ] INSERT.
* [ ] multi-statement.
* [ ] `pg_catalog`.
* [ ] `information_schema`.
* [ ] `pg_sleep`.

## Integration

* [ ] Conexión a analytics.
* [ ] Schema retrieval.
* [ ] Ejecución SELECT.
* [ ] Escritura rechazada.
* [ ] Timeout.
* [ ] Seed consistente.
* [ ] LangGraph end-to-end.

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

---

# 20. Fase 17 — Evaluación

Crear dataset con:

```text
question

expected_tables
expected_metric
expected_filters
expected_result
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

* [ ] SQL correcto.
* [ ] Resultado correcto.
* [ ] Tablas correctas.
* [ ] Filtros correctos.
* [ ] Latencia.
* [ ] Retries.
* [ ] Coste.
* [ ] Calidad de la respuesta.

---

# 21. Fase 18 — Observabilidad

Registrar por request:

```text
request_id

schema_ms
generate_sql_ms
validation_ms
database_ms
analysis_ms
answer_ms

total_ms

tokens
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
```

---

# 22. Funcionalidades futuras

Una vez estable el núcleo:

* [ ] Gráficas.
* [ ] CSV.
* [ ] Excel.
* [ ] Forecasting.
* [ ] RAG.
* [ ] Reportes programados.
* [ ] Alertas.
* [ ] Permisos por usuario.
* [ ] Acceso a múltiples datasets.
* [ ] Semantic layer avanzada.
* [ ] Dashboards.
* [ ] Auth empresarial.

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

---

# 24. Próximas acciones inmediatas

Orden recomendado para continuar desde el estado actual:

* [ ] Corregir y validar el seed.
* [ ] Crear todos los archivos DDL/DML dentro del repo.
* [ ] Implementar `schema.py`.
* [ ] Implementar carga de `data_dictionary.yaml`.
* [ ] Implementar `generate_sql.py`.
* [ ] Implementar `validate_sql.py`.
* [ ] Implementar `execute_sql.py`.
* [ ] Implementar `fix_sql.py`.
* [ ] Construir `StateGraph`.
* [ ] Conectar `/chat`.
* [ ] Agregar tests.
* [ ] Probar preguntas end-to-end.
* [ ] Agregar checkpointer PostgreSQL.
* [ ] Agregar Redis sessions/cache.

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

* [ ] El SQL es read-only.
* [ ] El SQL fue validado.
* [ ] La conexión es read-only.
* [ ] El usuario de PostgreSQL es read-only.
* [ ] Existe timeout.
* [ ] Existe límite de filas.
* [ ] El agente puede corregir SQL erróneo.
* [ ] Los resultados provienen únicamente de datos reales.
* [ ] Existe trazabilidad de la ejecución.

Ese será el punto en el que tendremos un **Data Analyst Agent funcional**, no solo una colección de contenedores con aspiraciones.
