from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    litellm_base_url: str
    litellm_master_key: str

    agent_database_url: str
    analytics_database_url: str

    redis_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()