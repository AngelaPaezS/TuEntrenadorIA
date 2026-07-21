"""Pruebas HTTP de la vista y la API sin consumir Cohere."""

from __future__ import annotations

from pathlib import Path
import unittest

import httpx

from tu_entrenador_ia.langchain_agent import AgentExecutionError
from tu_entrenador_ia.web_app import create_web_app
from tu_entrenador_ia.web_rate_limit import InMemoryRateLimiter
from tu_entrenador_ia.web_sessions import WebSessionStore

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_DIR = PROJECT_ROOT / "documents"


class _FakeWebAgent:
    """Agente predecible usado por TestClient."""

    def __init__(self) -> None:
        """Inicia sin historial."""

        self.turns = 0

    def ask(self, message: str) -> str:
        """Devuelve eco o simula un fallo controlado."""

        if message == "fallar":
            raise AgentExecutionError("fallo interno simulado")
        self.turns += 1
        return f"Respuesta {self.turns}: {message}"

    def clear_history(self) -> None:
        """Reinicia el contador."""

        self.turns = 0


class WebAppTests(unittest.IsolatedAsyncioTestCase):
    """Comprueba página, validación, sesiones y encabezados."""

    async def asyncSetUp(self) -> None:
        """Crea una aplicación sin credenciales ni red."""

        store = WebSessionStore(_FakeWebAgent)
        application = create_web_app(
            documents_directory=DOCUMENTS_DIR,
            project_directory=PROJECT_ROOT,
            session_store=store,
        )
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application),
            base_url="http://testserver",
        )

    async def asyncTearDown(self) -> None:
        """Cierra el cliente HTTP de prueba."""

        await self.client.aclose()

    async def test_serves_simple_frontend_and_assets(self) -> None:
        """HTML, CSS, JavaScript y logotipo deben estar disponibles."""

        page = await self.client.get("/")
        self.assertEqual(200, page.status_code)
        self.assertIn("Tu Entrenador IA", page.text)
        self.assertIn('src="/app.js"', page.text)
        self.assertEqual(200, (await self.client.get("/styles.css")).status_code)
        self.assertEqual(200, (await self.client.get("/app.js")).status_code)
        self.assertEqual(
            200,
            (await self.client.get("/assets/logo.png")).status_code,
        )

    async def test_health_endpoint_and_security_headers(self) -> None:
        """Render debe recibir salud y el navegador encabezados defensivos."""

        response = await self.client.get("/api/health")
        self.assertEqual({"status": "ok"}, response.json())
        self.assertEqual("nosniff", response.headers["x-content-type-options"])
        self.assertIn(
            "default-src 'self'",
            response.headers["content-security-policy"],
        )

    async def test_chat_requires_policy_acceptance(self) -> None:
        """El backend no debe confiar solamente en el estado visual."""

        response = await self.client.post(
            "/api/chat",
            json={
                "message": "Hola",
                "session_id": None,
                "accepted_policies": False,
            },
        )
        self.assertEqual(403, response.status_code)

    async def test_chat_keeps_session_and_reset_removes_it(self) -> None:
        """Dos mensajes conservan memoria hasta solicitar reinicio."""

        first = await self._chat("Hola")
        second = await self._chat("Otra pregunta", first["session_id"])
        self.assertEqual(first["session_id"], second["session_id"])
        self.assertEqual("Respuesta 2: Otra pregunta", second["answer"])

        reset = await self.client.post(
            "/api/session/reset",
            json={"session_id": first["session_id"]},
        )
        self.assertEqual({"reset": True}, reset.json())
        after_reset = await self._chat("Nuevo", first["session_id"])
        self.assertNotEqual(first["session_id"], after_reset["session_id"])
        self.assertEqual("Respuesta 1: Nuevo", after_reset["answer"])

    async def test_rejects_empty_long_or_extra_fields(self) -> None:
        """Pydantic debe limitar el cuerpo recibido antes de usar Cohere."""

        for payload in (
            {"message": "", "session_id": None, "accepted_policies": True},
            {"message": "x" * 2_001, "session_id": None, "accepted_policies": True},
            {
                "message": "Hola",
                "session_id": None,
                "accepted_policies": True,
                "unexpected": "value",
            },
        ):
            with self.subTest(payload_length=len(payload["message"])):
                response = await self.client.post("/api/chat", json=payload)
                self.assertEqual(422, response.status_code)

    async def test_agent_error_is_safe_for_browser(self) -> None:
        """La respuesta pública no debe incluir excepciones internas."""

        response = await self.client.post(
            "/api/chat",
            json={
                "message": "fallar",
                "session_id": None,
                "accepted_policies": True,
            },
        )
        self.assertEqual(502, response.status_code)
        self.assertNotIn("interno simulado", response.text)

    async def test_chat_rate_limit_protects_external_api(self) -> None:
        """Una IP no debe poder consumir Cohere sin un límite básico."""

        application = create_web_app(
            documents_directory=DOCUMENTS_DIR,
            project_directory=PROJECT_ROOT,
            session_store=WebSessionStore(_FakeWebAgent),
            rate_limiter=InMemoryRateLimiter(
                max_requests=1,
                window_seconds=60,
            ),
        )
        client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application),
            base_url="http://testserver",
        )
        try:
            payload = {
                "message": "Hola",
                "session_id": None,
                "accepted_policies": True,
            }
            first = await client.post("/api/chat", json=payload)
            self.assertEqual(200, first.status_code)
            limited = await client.post("/api/chat", json=payload)
        finally:
            await client.aclose()

        self.assertEqual(429, limited.status_code)
        self.assertEqual("60", limited.headers["retry-after"])

    async def _chat(
        self,
        message: str,
        session_id: str | None = None,
    ) -> dict[str, str]:
        """Envía un mensaje válido y devuelve el JSON comprobado."""

        response = await self.client.post(
            "/api/chat",
            json={
                "message": message,
                "session_id": session_id,
                "accepted_policies": True,
            },
        )
        self.assertEqual(200, response.status_code)
        return response.json()


if __name__ == "__main__":
    unittest.main()
