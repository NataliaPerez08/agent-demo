# Manual de Usuario — Data Analyst Agent

## Tabla de contenidos

1. [Introducción](#1-introducción)
2. [Acceso al sistema](#2-acceso-al-sistema)
3. [Chatbot (Chainlit)](#3-chatbot-chainlit)
4. [API REST](#4-api-rest)
5. [Dashboards](#5-dashboards)
6. [Export de resultados](#6-export-de-resultados)
7. [Modelos de IA](#7-modelos-de-ia)
8. [MCP — integración con Claude Desktop](#8-mcp--integración-con-claude-desktop)
9. [Preguntas frecuentes](#9-preguntas-frecuentes)
10. [Solución de problemas](#10-solución-de-problemas)

---

## 1. Introducción

El **Data Analyst Agent** es un asistente de inteligencia de negocios
que responde preguntas en lenguaje natural sobre tus datos de ventas.

**¿Qué puede hacer?**

- Responder preguntas como "¿Cuánto revenue hubo en julio?"
- Generar SQL seguro y validado automáticamente
- Analizar tendencias, rankings y comparaciones
- Sugerir gráficas (barras, líneas, torta)
- Exportar resultados a CSV o Excel
- Mantener contexto conversacional ("¿Y solo los de México?")
- Crear dashboards con widgets persistentes
- Funcionar como herramienta para Claude Desktop vía MCP

**¿Qué NO puede hacer?**

- Modificar datos (las consultas son 100% read-only)
- Inventar datos (solo usa datos reales de la base)
- Acceder a tablas del sistema (`pg_catalog`, `information_schema`)
- Ejecutar consultas que tarden más de 5 segundos

---

## 2. Acceso al sistema

### Chatbot web (recomendado para usuarios finales)

```
http://localhost:8001
```

Abre esta URL en tu navegador. Verás una interfaz de chat donde
puedes escribir preguntas directamente.

### API REST (para desarrolladores e integraciones)

```
http://localhost:8000
```

Endpoints disponibles:

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/health` | GET | Verificar que el servicio está activo |
| `/chat` | POST | Hacer una pregunta al agente |
| `/export` | GET | Descargar resultados en CSV/XLSX |
| `/dashboards` | POST/GET | Crear y listar dashboards |
| `/dashboards/{id}` | GET/DELETE | Ver o eliminar un dashboard |
| `/dashboards/{id}/widgets` | POST | Añadir widget a un dashboard |
| `/dashboards/{id}/render` | GET | Renderizar un dashboard completo |
| `/mcp` | POST | Endpoint MCP para Claude Desktop |

### Documentación interactiva

```
http://localhost:8000/docs    (Swagger UI)
http://localhost:8000/redoc    (ReDoc)
```

---

## 3. Chatbot (Chainlit)

### Primer uso

1. Abre `http://localhost:8001` en tu navegador.
2. Verás un mensaje de bienvenida con ejemplos de preguntas.
3. Escribe tu pregunta en el campo de texto y presiona Enter.

### Ejemplos de preguntas

```
¿Cuánto revenue hubo en julio?
¿Cuáles fueron los 5 clientes con más revenue?
¿Qué país generó más revenue?
Compara junio contra julio.
¿Qué productos vendieron más unidades?
¿Cuál fue el ticket promedio?
```

### Follow-ups conversacionales

El agente recuerda el contexto de la conversación. Puedes hacer
preguntas de seguimiento sin repetir todo:

```
Tú:     ¿Cuáles fueron los mejores clientes?
Agente: Los cinco clientes con mayor revenue fueron...

Tú:     ¿Y solo los de México?
Agente: Filtrando por México, los clientes con mayor revenue...
```

### Lo que ves en cada respuesta

Cada respuesta del agente incluye:

- **Respuesta en lenguaje natural** — conclusión + datos relevantes + contexto
- **SQL generado** — el código SQL que se ejecutó (en un bloque de código)
- **Gráfica sugerida** — tipo de chart + ejes (en el panel lateral)
- **Botones de export** — CSV y Excel para descargar los resultados

### Exportar desde el chatbot

1. Después de cualquier respuesta, verás dos botones:
   - 📊 **Exportar CSV**
   - 📈 **Exportar Excel**
2. Haz clic en el formato deseado.
3. El archivo se descargará automáticamente.

---

## 4. API REST

### Health check

```bash
curl http://localhost:8000/health
```

Respuesta:

```json
{"status": "ok"}
```

### Hacer una pregunta

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Cuáles fueron los 5 clientes con más revenue?",
    "user_id": "mi-usuario"
  }'
```

Respuesta:

```json
{
  "thread_id": "a1b2c3d4-...",
  "answer": "Los cinco clientes con mayor revenue fueron Stark Industries...",
  "sql": "SELECT c.name, SUM(o.total) AS revenue FROM customers c ...",
  "chart": {
    "type": "bar",
    "title": "5 clientes con más revenue",
    "x": "name",
    "y": "revenue",
    "columns": ["name", "revenue"]
  }
}
```

### Parámetros del `/chat`

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `question` | string | Sí | La pregunta en lenguaje natural |
| `user_id` | string | No | Identificador del usuario (default: `anon`) |

### Rate limiting

- Máximo **30 peticiones por minuto** por usuario.
- Si excedes el límite, recibes `429 Too Many Requests`.
- El `user_id` se usa para asociar la sesión y el rate limit.

### Sesiones y follow-ups

El mismo `user_id` reutiliza automáticamente el `thread_id` de la
sesión anterior. Esto habilita follow-ups conversacionales sin
gestión manual de IDs.

Si quieres iniciar una conversación nueva, usa un `user_id` diferente.

---

## 5. Dashboards

Los dashboards permiten guardar preguntas frecuentes como **widgets**
persistentes y re-ejecutarlas todas a la vez.

### Crear un dashboard

```bash
curl -X POST http://localhost:8000/dashboards \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ventas Q3",
    "description": "Dashboard de ventas del tercer trimestre",
    "user_id": "mi-usuario"
  }'
```

Respuesta:

```json
{
  "id": 1,
  "name": "Ventas Q3",
  "description": "Dashboard de ventas del tercer trimestre",
  "user_id": "mi-usuario",
  "widgets": []
}
```

### Listar dashboards

```bash
curl "http://localhost:8000/dashboards?user_id=mi-usuario"
```

### Ver un dashboard con sus widgets

```bash
curl http://localhost:8000/dashboards/1
```

### Añadir un widget (pregunta) al dashboard

```bash
curl -X POST http://localhost:8000/dashboards/1/widgets \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Revenue mensual",
    "question": "¿Cuánto revenue hubo en julio?",
    "chart_type": "bar"
  }'
```

Puedes añadir varios widgets a un mismo dashboard:

```bash
# Widget 2
curl -X POST http://localhost:8000/dashboards/1/widgets \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Top 5 clientes",
    "question": "¿Cuáles fueron los 5 clientes con más revenue?"
  }'

# Widget 3
curl -X POST http://localhost:8000/dashboards/1/widgets \
  -H "Content-Type: application/json" \
  -d '{
    "title": "País top",
    "question": "¿Qué país generó más revenue?"
  }'
```

### Renderizar un dashboard

```bash
curl http://localhost:8000/dashboards/1/render
```

Esto **re-ejecuta todas las preguntas** de los widgets y devuelve:

```json
{
  "dashboard_id": 1,
  "name": "Ventas Q3",
  "widgets": [
    {
      "widget_id": 1,
      "title": "Revenue mensual",
      "question": "¿Cuánto revenue hubo en julio?",
      "answer": "El revenue de julio fue 52,500...",
      "sql": "SELECT SUM(total) FROM orders WHERE ...",
      "chart": {"type": "bar", "title": "Revenue mensual", ...},
      "rows": 1
    },
    {
      "widget_id": 2,
      "title": "Top 5 clientes",
      "question": "¿Cuáles fueron los 5 clientes con más revenue?",
      "answer": "Los cinco clientes con mayor revenue fueron...",
      "sql": "SELECT c.name, SUM(o.total) ...",
      "chart": {"type": "bar", ...},
      "rows": 5
    }
  ]
}
```

> **Nota**: El render puede tardar varios segundos si hay muchos
> widgets (cada uno ejecuta el pipeline completo: schema → SQL →
> validate → execute → analyze → answer).

### Eliminar un widget

```bash
curl -X DELETE http://localhost:8000/dashboards/1/widgets/2
```

### Eliminar un dashboard

```bash
curl -X DELETE http://localhost:8000/dashboards/1
```

> Eliminar un dashboard borra todos sus widgets en cascada.

---

## 6. Export de resultados

### Desde la API

```bash
# CSV
curl -o resultados.csv \
  "http://localhost:8000/export?thread_id=a1b2c3d4-...&fmt=csv"

# Excel
curl -o resultados.xlsx \
  "http://localhost:8000/export?thread_id=a1b2c3d4-...&fmt=xlsx"
```

### Parámetros

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `thread_id` | string | (requerido) | ID devuelto por `/chat` |
| `fmt` | string | `csv` | Formato: `csv` o `xlsx` |

### Notas

- Los resultados se cachean por **1 hora** después de la consulta.
- Si el `thread_id` no tiene resultados recientes, recibes `404`.
- El export devuelve los datos de la **última consulta** de esa sesión.

---

## 7. Modelos de IA

El agente soporta dos backends de modelos:

### OpenAI (requiere API key)

| Alias | Modelo | Uso |
|-------|--------|-----|
| `analyst-smart` | gpt-5 | Default, máxima calidad |
| `analyst-fast` | gpt-5-mini | Respuestas rápidas |

### Ollama (local, sin API key, sin coste)

| Alias | Modelo | Uso |
|-------|--------|-----|
| `analyst-local` | qwen2.5:7b | Máxima calidad local |
| `analyst-local-fast` | qwen2.5:1.5b | Rápido, recomendado para tests |

### Cambiar el modelo

Edita el archivo `.env`:

```env
# OpenAI (requiere API key)
ANALYST_MODEL=analyst-smart

# Ollama (sin coste)
ANALYST_MODEL=analyst-local-fast
```

Reinicia el servicio después de cambiar:

```bash
docker compose restart api
```

### ¿Cuál usar?

| Escenario | Modelo recomendado |
|-----------|-------------------|
| Producción con presupuesto | `analyst-smart` (gpt-5) |
| Desarrollo rápido | `analyst-fast` (gpt-5-mini) |
| Sin API key / sin coste | `analyst-local-fast` (qwen2.5:1.5b) |
| Máxima calidad local | `analyst-local` (qwen2.5:7b) |
| CPU únicamente | `analyst-local-fast` (1.5b es ligero) |

---

## 8. MCP — Integración con Claude Desktop

El agente expone la herramienta `ask_analytics` vía MCP (Model
Context Protocol). Esto permite que **Claude Desktop** use el agente
como una herramienta más.

### Configurar Claude Desktop

1. Abre el archivo de configuración de Claude Desktop:

   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

2. Añade la configuración del servidor MCP:

   ```json
   {
     "mcpServers": {
       "data-analyst-agent": {
         "url": "http://localhost:8000/mcp"
       }
     }
   }
   ```

   Si el agente está en otro servidor, reemplaza `localhost:8000` por
   la URL correspondiente.

3. Reinicia Claude Desktop.

4. Ahora puedes preguntar a Claude:

   ```
   Pregunta al data analyst agent: ¿Cuánto revenue hubo en julio?
   ```

   Claude usará la herramienta `ask_analytics` automáticamente y te
   devolverá la respuesta + el SQL generado.

### ¿Qué hace `ask_analytics`?

- Recibe una pregunta en lenguaje natural
- La procesa a través del pipeline completo del agente
- Devuelve la respuesta + el SQL generado
- Cada llamada usa un `thread_id` independiente (no afecta sesiones del chatbot)

---

## 9. Preguntas frecuentes

### ¿El agente puede modificar mis datos?

**No.** Todas las consultas son read-only. El agente usa un rol
PostgreSQL sin permisos de escritura, las conexiones son read-only,
y el validador SQL bloquea cualquier operación DDL/DML (INSERT,
UPDATE, DELETE, DROP, etc.).

### ¿Qué pasa si el agente no puede responder?

Si la pregunta no puede responderse con los datos disponibles, el
agente devuelve:

```
No fue posible responder la pregunta. Motivo: La pregunta no puede
responderse con el esquema.
```

### ¿Puedo hacer follow-ups en la API?

Sí. Usa el mismo `user_id` en peticiones consecutivas. El agente
reutiliza el `thread_id` automáticamente.

### ¿Cuánto tarda una respuesta?

- Con OpenAI gpt-5: 1-3 segundos típicamente
- Con Ollama qwen2.5:1.5b en CPU: 5-15 segundos
- Con Ollama qwen2.5:7b en CPU: 15-60 segundos
- Con GPU: significativamente más rápido

### ¿Los resultados están cacheados?

Sí. Los resultados de consultas idénticas se cachean en Redis por
5 minutos. El schema se cachea por 1 hora.

### ¿Puedo usar el agente sin OpenAI?

Sí. Configura `ANALYST_MODEL=analyst-local-fast` en `.env` y usa
Ollama. No necesitas `OPENAI_API_KEY`.

### ¿Qué datos tiene la base?

La base analítica contiene datos de demostración:
- 8 clientes (México, Colombia, Estados Unidos)
- 5 productos (analytics, integration, ai, services)
- 24 órdenes (mayo-julio 2026, estados: completed, cancelled, refunded)
- Líneas de orden con cantidades y precios

### ¿Puedo añadir mis propios datos?

Sí, pero requiere acceso a la base analítica. Los datos se cargan
via SQL (`database/analytics/dml/001_seed.sql`). Consulta con el
administrador de la base de datos.

---

## 10. Solución de problemas

### El chatbot no carga

**Síntoma**: `http://localhost:8001` no responde.

**Solución**:
```bash
# Verificar que el stack esté corriendo
docker compose ps

# Si no está, levantarlo
docker compose up --build

# Ver logs del chatbot
docker compose logs chatbot
```

### El agente responde "El API del agente no está disponible"

**Causa**: El chatbot no puede conectar con la API.

**Solución**:
```bash
# Verificar que la API esté saludable
curl http://localhost:8000/health

# Si no responde, revisar logs
docker compose logs api
```

### Error 429 "Demasiadas solicitudes"

**Causa**: Excediste el rate limit (30 req/min).

**Solución**: Espera 60 segundos y vuelve a intentar.

### El agente tarda mucho en responder

**Causa probable**: Modelo local en CPU.

**Solución**:
- Usa `analyst-local-fast` (qwen2.5:1.5b) en lugar de `analyst-local` (7b)
- O cambia a `analyst-smart` (OpenAI) si tienes API key
- O usa GPU (configura el node pool GPU en CCE)

### Error "No hay resultados recientes para este thread_id"

**Causa**: Intentas exportar resultados de una sesión que ya expiró
(TTL 1 hora) o que no existe.

**Solución**: Vuelve a hacer la pregunta via `/chat` y exporta
inmediatamente después.

### Ollama no descarga los modelos

**Síntoma**: El job `ollama-init` falla o tarda indefinidamente.

**Solución**:
```bash
# Ver logs del job
docker compose logs ollama-init

# Reiniciar el job
docker compose up ollama-init

# Verificar que ollama esté healthy
docker compose ps ollama
```

### El SQL aparece como "CANNOT_ANSWER"

**Causa**: El agente determinó que la pregunta no puede responderse
con el esquema disponible.

**Solución**: Reformula la pregunta usando términos del negocio
(revenue, clientes, órdenes, productos, países).

### Dashboards no se guardan

**Causa**: La agent DB no está accesible.

**Solución**:
```bash
# Verificar que PostgreSQL agent esté corriendo
docker compose ps app-postgres

# Ver logs
docker compose logs app-postgres
```

### Contacto

Para soporte técnico, revisa:
- **Logs**: `docker compose logs <servicio>`
- **Documentación técnica**: `README.md`, `ARCHITECTURE.md`
- **Plan de acción**: `action_plan.md`
- **Manifests de deploy**: `deploy/cce/README.md`