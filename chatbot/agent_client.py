"""Cliente HTTP async para el endpoint /chat del data analyst agent."""

import httpx


class AgentClient:
    """Cliente async para POST /chat y GET /export."""

    def __init__(self, base_url: str, timeout: float = 120.0):

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def chat(
        self, question: str, user_id: str = "chainlit", model: str | None = None
    ) -> dict:
        """Envia una pregunta al agente y devuelve la respuesta completa.

        Returns:
            dict con thread_id, answer, sql, chart, rows, row_count
        """

        payload: dict = {"question": question, "user_id": user_id}
        if model:
            payload["model"] = model

        async with httpx.AsyncClient(timeout=self.timeout) as client:

            response = await client.post(
                f"{self.base_url}/chat",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def export_csv(self, thread_id: str) -> bytes:
        """Descarga los resultados del thread en CSV."""

        async with httpx.AsyncClient(timeout=self.timeout) as client:

            response = await client.get(
                f"{self.base_url}/export",
                params={"thread_id": thread_id, "fmt": "csv"},
            )
            response.raise_for_status()
            return response.content

    async def export_excel(self, thread_id: str) -> bytes:
        """Descarga los resultados del thread en XLSX."""

        async with httpx.AsyncClient(timeout=self.timeout) as client:

            response = await client.get(
                f"{self.base_url}/export",
                params={"thread_id": thread_id, "fmt": "xlsx"},
            )
            response.raise_for_status()
            return response.content

    async def health(self) -> bool:
        """Checkea si el API esta listo."""

        try:

            async with httpx.AsyncClient(timeout=5) as client:

                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200

        except Exception:

            return False

    async def get_models(self) -> list[dict]:
        """Obtiene la lista de modelos disponibles del API."""

        try:

            async with httpx.AsyncClient(timeout=5) as client:

                response = await client.get(f"{self.base_url}/models")
                response.raise_for_status()
                return response.json().get("models", [])

        except Exception:

            return []