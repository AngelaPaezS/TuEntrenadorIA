"""Aplicación FastAPI que conecta la vista estática con Coach IA."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .coach import CoachIA
from .langchain_agent import AgentExecutionError
from .retrieval import DocumentCorpus
from .settings import CohereSettings
from .web_sessions import WebAgentFactory, WebSessionStore


class ChatRequest(BaseModel):
    """Mensaje validado enviado por la página web."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=2_000)
    session_id: UUID | None = None
    accepted_policies: bool


class ChatResponse(BaseModel):
    """Respuesta del agente junto con el identificador de conversación."""

    session_id: UUID
    answer: str


class ResetRequest(BaseModel):
    """Identificador requerido para eliminar una sesión web."""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID


class ResetResponse(BaseModel):
    """Confirma si la sesión solicitada existía."""

    reset: bool


def create_web_app(
    *,
    documents_directory: Path,
    project_directory: Path,
    coach: CoachIA | None = None,
    session_store: WebSessionStore | None = None,
) -> FastAPI:
    """Construye la API con dependencias reales o dobles para pruebas."""

    resolved_project = project_directory.resolve()
    web_directory = resolved_project / "web"
    if not web_directory.is_dir():
        raise RuntimeError(f"No existe la carpeta web: {web_directory}")

    if session_store is None:
        resolved_coach = coach or CoachIA.from_directory(documents_directory)
        settings = CohereSettings.from_project(resolved_project)
        corpus = DocumentCorpus.build(
            documents_directory,
            cache_path=resolved_project / ".cache" / "document_chunks.json",
        )
        agent_factory = WebAgentFactory(resolved_coach, corpus, settings)
        session_store = WebSessionStore(agent_factory.create)

    store = session_store

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        """Expone dependencias en el estado durante la vida de la aplicación."""

        application.state.session_store = store
        yield

    app = FastAPI(
        title="Tu Entrenador IA",
        version="0.3.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        """Agrega encabezados defensivos tanto a la API como al frontend."""

        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; "
            "style-src 'self'; script-src 'self'; connect-src 'self'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        return response

    @app.exception_handler(AgentExecutionError)
    async def agent_error_handler(
        request: Request,
        error: AgentExecutionError,
    ) -> JSONResponse:
        """Convierte fallos controlados del agente en un mensaje web seguro."""

        del request, error
        return JSONResponse(
            status_code=502,
            content={
                "detail": (
                    "Coach IA no pudo responder en este momento. "
                    "Inténtalo nuevamente."
                )
            },
        )

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        """Permite a OCI comprobar que el proceso está disponible."""

        return {"status": "ok"}

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(payload: ChatRequest) -> ChatResponse:
        """Envía el mensaje al agente de la sesión sin bloquear el servidor."""

        if not payload.accepted_policies:
            raise HTTPException(
                status_code=403,
                detail="Debes aceptar las políticas antes de iniciar el chat.",
            )
        session_id, answer = await asyncio.to_thread(
            store.ask,
            payload.session_id,
            payload.message,
        )
        return ChatResponse(session_id=session_id, answer=answer)

    @app.post("/api/session/reset", response_model=ResetResponse)
    async def reset_session(payload: ResetRequest) -> ResetResponse:
        """Elimina el historial temporal solicitado."""

        reset = await asyncio.to_thread(store.reset, payload.session_id)
        return ResetResponse(reset=reset)

    app.mount("/", StaticFiles(directory=web_directory, html=True), name="web")
    return app
