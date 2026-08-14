                         ┌──────────────────────┐
                         │       Usuario        │
                         └──────────┬───────────┘
                                    │ HTTP
                                    ▼
                         ┌──────────────────────┐
                         │ FastAPI / LangChain  │
                         │      Agent API       │
                         └──────────┬───────────┘
                                    │
                  ┌─────────────────┼─────────────────┐
                  │                 │                 │
                  ▼                 ▼                 ▼
        ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
        │    LiteLLM     │ │   PostgreSQL   │ │     Redis      │
        │    Gateway     │ │                │ │                │
        ├────────────────┤ ├────────────────┤ ├────────────────┤
        │ OpenAI         │ │ checkpoints    │ │ sesiones       │
        │ Anthropic      │ │ historial      │ │ rate limit     │
        │ Gemini         │ │ metadata       │ │ cache          │
        │ modelos local  │ │ memoria        │ │ locks          │
        └────────────────┘ └────────────────┘ └────────────────┘