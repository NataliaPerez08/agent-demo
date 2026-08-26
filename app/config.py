from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    litellm_base_url: str
    litellm_master_key: str

    agent_database_url: str
    analytics_database_url: str

    redis_url: str

    maas_api_key: str = ""

    # Alias de modelo expuesto por LiteLLM.
    # Valores validos: analyst-smart, analyst-fast (OpenAI via LiteLLM),
    # analyst-local, analyst-local-fast (Ollama via LiteLLM).
    analyst_model: str = "analyst-smart"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()