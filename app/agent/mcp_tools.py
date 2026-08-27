"""Nodos del grafo para el loop reactivo con tools MCP.

agent_with_tools: LLM con bind_tools(mcp_tools) que decide llamar
   tools o dar la respuesta final.
mcp_answer: extrae la respuesta final del ultimo mensaje del loop.
"""

from langchain_core.messages import HumanMessage

from app.infrastructure.llm import _model_name, get_llm
from app.infrastructure.observability import get_observation


def make_agent_with_tools(mcp_tools: list):
    """Factory del nodo agent_with_tools.

    Necesita las tools MCP en closure para bind_tools.
    """

    async def agent_with_tools(state):

        llm = get_llm()
        llm_with_tools = llm.bind_tools(mcp_tools)

        messages = state.get("messages") or []

        if not messages:
            messages = [HumanMessage(content=state["question"])]

        response = await llm_with_tools.ainvoke(messages)

        obs = get_observation()

        if obs is not None:

            usage = {}

            meta = getattr(response, "usage_metadata", None)

            if isinstance(meta, dict):
                usage = meta

            if not usage:
                resp_meta = getattr(response, "response_metadata", {}) or {}
                token_usage = (
                    resp_meta.get("token_usage")
                    or resp_meta.get("usage")
                    or {}
                )
                if isinstance(token_usage, dict):
                    usage = {
                        "input_tokens": token_usage.get(
                            "prompt_tokens", token_usage.get("input_tokens", 0)
                        ),
                        "output_tokens": token_usage.get(
                            "completion_tokens",
                            token_usage.get("output_tokens", 0),
                        ),
                    }

            obs.add_tokens(
                _model_name(llm),
                usage.get("input_tokens", usage.get("prompt_tokens", 0)),
                usage.get("output_tokens", usage.get("completion_tokens", 0)),
            )

        return {"messages": [response]}

    return agent_with_tools


async def mcp_answer(state):

    messages = state.get("messages") or []
    last = messages[-1] if messages else None

    content = ""

    if last:
        raw = getattr(last, "content", "")
        content = raw if isinstance(raw, str) else str(raw)

    return {"answer": content.strip(), "success": True}