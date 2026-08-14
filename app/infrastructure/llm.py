from langchain_openai import ChatOpenAI

from app.config import settings
from app.infrastructure.observability import get_observation


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


def _model_name(llm: ChatOpenAI) -> str:

    return getattr(llm, "model_name", None) or getattr(llm, "model", "unknown")


async def ainvoke_with_usage(llm: ChatOpenAI, messages: list) -> str:
    """Invoca el LLM y acumula tokens/coste en la observacion activa.

    Devuelve el contenido de la respuesta (str).
    """

    response = await llm.ainvoke(messages)

    content = response.content if isinstance(response.content, str) else str(response.content)

    obs = get_observation()

    if obs is not None:

        usage = {}

        meta = getattr(response, "usage_metadata", None)

        if isinstance(meta, dict):

            usage = meta

        if not usage:

            resp_meta = getattr(response, "response_metadata", {}) or {}

            token_usage = resp_meta.get("token_usage") or resp_meta.get("usage") or {}

            if isinstance(token_usage, dict):

                usage = {
                    "input_tokens": token_usage.get("prompt_tokens", token_usage.get("input_tokens", 0)),
                    "output_tokens": token_usage.get("completion_tokens", token_usage.get("output_tokens", 0)),
                }

        obs.add_tokens(
            _model_name(llm),
            usage.get("input_tokens", usage.get("prompt_tokens", 0)),
            usage.get("output_tokens", usage.get("completion_tokens", 0)),
        )

    return content