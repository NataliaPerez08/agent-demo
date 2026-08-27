import contextvars
import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger("observability")


# Tarifas USD por 1 millon de tokens (placeholder, sobreescribibles).
MODEL_RATES = {
    "analyst-fast": {"input": 0.15, "output": 0.60},
    "analyst-smart": {"input": 1.50, "output": 6.00},
    # Modelos locales (Ollama): sin coste.
    "analyst-local": {"input": 0.0, "output": 0.0},
    "analyst-local-fast": {"input": 0.0, "output": 0.0},
}


@dataclass
class Observation:

    request_id: str
    phases: dict[str, int] = field(default_factory=dict)

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    models: set[str] = field(default_factory=set)

    def record_phase(self, name: str, ms: int) -> None:
        self.phases[name] = int(ms)

    def add_tokens(self, model: str, prompt: int, completion: int) -> None:

        prompt = int(prompt or 0)
        completion = int(completion or 0)

        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens = self.prompt_tokens + self.completion_tokens

        if model:
            self.models.add(model)

        rate = MODEL_RATES.get(model, MODEL_RATES.get("analyst-smart"))
        self.estimated_cost += (
            prompt * rate["input"] / 1_000_000
            + completion * rate["output"] / 1_000_000
        )


current_obs: contextvars.ContextVar[Observation | None] = contextvars.ContextVar(
    "current_obs", default=None
)


def get_observation() -> Observation | None:
    return current_obs.get()


def set_observation(obs: Observation) -> contextvars.Token:
    return current_obs.set(obs)


def reset_observation(token: contextvars.Token) -> None:
    current_obs.reset(token)


def timed(phase: str):
    """Decorador para nodos async: mide y registra la duracion de la fase."""

    def decorator(fn):

        async def wrapper(state):

            start = time.perf_counter()

            result = await fn(state)

            ms = int((time.perf_counter() - start) * 1000)

            obs = current_obs.get()

            if obs is not None:

                obs.record_phase(phase, ms)

            return result

        return wrapper

    return decorator


PHASE_ORDER = (
    "schema",
    "generate_sql",
    "validate_sql",
    "execute_sql",
    "fix_sql",
    "analyze",
    "answer",
)


def format_observation(obs: Observation) -> str:
    """Linea estructurada por request, estilo el del plan (fase 18)."""

    phases = "  ".join(
        f"{p}={obs.phases[p]}ms"
        for p in PHASE_ORDER
        if p in obs.phases
    )

    total_ms = sum(obs.phases.values())

    return (
        f"request: {obs.request_id}\n"
        f"{phases}\n"
        f"total={total_ms}ms\n"
        f"tokens in={obs.prompt_tokens} out={obs.completion_tokens} "
        f"total={obs.total_tokens} cost=${obs.estimated_cost:.6f}"
    )


def log_observation(obs: Observation) -> None:

    try:

        logger.info(format_observation(obs))

    except Exception:

        pass