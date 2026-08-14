from langchain_openai import ChatOpenAI

from app.config import settings


def get_llm(
    model: str = "analyst-smart",
    temperature: float = 0,
) -> ChatOpenAI:

    return ChatOpenAI(
        model=model,
        base_url=settings.litellm_base_url,
        api_key=settings.litellm_master_key,
        temperature=temperature,
    )