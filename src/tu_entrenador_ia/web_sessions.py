"""Sesiones web aisladas y temporales para conversaciones con Coach IA."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock
from time import monotonic
from typing import Protocol
from uuid import UUID, uuid4

from .coach import CoachIA
from .langchain_agent import LangChainCoachAgent
from .retrieval import DocumentCorpus
from .settings import CohereSettings


class ConversationalAgent(Protocol):
    """Contrato mínimo necesario para administrar una conversación."""

    def ask(self, message: str) -> str:
        """Responde un mensaje usando el historial de su propia sesión."""

    def clear_history(self) -> None:
        """Elimina la memoria temporal de la sesión."""


class WebAgentFactory:
    """Crea agentes por sesión compartiendo conocimiento ya procesado."""

    __slots__ = ("_coach", "_corpus", "_settings")

    def __init__(
        self,
        coach: CoachIA,
        corpus: DocumentCorpus,
        settings: CohereSettings,
    ) -> None:
        """Conserva dependencias inmutables para evitar reprocesar documentos."""

        self._coach = coach
        self._corpus = corpus
        self._settings = settings

    def create(self) -> LangChainCoachAgent:
        """Crea una conversación con la aceptación de políticas ya verificada."""

        return LangChainCoachAgent(
            coach=self._coach,
            corpus=self._corpus,
            settings=self._settings,
            additional_system_context=(
                "El usuario aceptó explícitamente las políticas de uso en la "
                "interfaz web. Para generar_rutina_validada debes usar "
                "accepted_policies=true."
            ),
        )


@dataclass(slots=True)
class _SessionEntry:
    """Agente, candado y tiempo de actividad asociados a una sesión."""

    agent: ConversationalAgent
    last_activity: float
    lock: Lock = field(default_factory=Lock)


class WebSessionStore:
    """Almacén en memoria con aislamiento, caducidad y capacidad limitada."""

    __slots__ = (
        "_agent_factory",
        "_sessions",
        "_sessions_lock",
        "_ttl_seconds",
        "_max_sessions",
        "_clock",
    )

    def __init__(
        self,
        agent_factory: Callable[[], ConversationalAgent],
        *,
        ttl_seconds: float = 1_800,
        max_sessions: int = 100,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        """Configura límites defensivos sin persistir conversaciones en disco."""

        if ttl_seconds <= 0:
            raise ValueError("La vigencia de sesión debe ser positiva.")
        if max_sessions < 1:
            raise ValueError("Debe permitirse al menos una sesión.")
        self._agent_factory = agent_factory
        self._sessions: dict[UUID, _SessionEntry] = {}
        self._sessions_lock = Lock()
        self._ttl_seconds = ttl_seconds
        self._max_sessions = max_sessions
        self._clock = clock

    @property
    def active_sessions(self) -> int:
        """Devuelve el número actual sin exponer identificadores."""

        with self._sessions_lock:
            return len(self._sessions)

    def ask(
        self,
        session_id: UUID | None,
        message: str,
    ) -> tuple[UUID, str]:
        """Obtiene o crea una sesión y serializa sus llamadas al modelo."""

        current_session_id, entry = self._get_or_create(session_id)
        with entry.lock:
            response = entry.agent.ask(message)
            entry.last_activity = self._clock()
        return current_session_id, response

    def reset(self, session_id: UUID) -> bool:
        """Elimina una sesión completa y devuelve si estaba activa."""

        with self._sessions_lock:
            entry = self._sessions.pop(session_id, None)
        if entry is None:
            return False
        with entry.lock:
            entry.agent.clear_history()
        return True

    def _get_or_create(
        self,
        session_id: UUID | None,
    ) -> tuple[UUID, _SessionEntry]:
        """Recupera una sesión vigente o crea una con identificador aleatorio."""

        now = self._clock()
        with self._sessions_lock:
            self._remove_expired(now)
            if session_id is not None:
                existing = self._sessions.get(session_id)
                if existing is not None:
                    existing.last_activity = now
                    return session_id, existing

            if len(self._sessions) >= self._max_sessions:
                oldest_id = min(
                    self._sessions,
                    key=lambda current_id: self._sessions[current_id].last_activity,
                )
                self._sessions.pop(oldest_id, None)

            new_session_id = uuid4()
            entry = _SessionEntry(
                agent=self._agent_factory(),
                last_activity=now,
            )
            self._sessions[new_session_id] = entry
            return new_session_id, entry

    def _remove_expired(self, now: float) -> None:
        """Elimina entradas vencidas; se llama con el candado global adquirido."""

        expired_ids = [
            session_id
            for session_id, entry in self._sessions.items()
            if now - entry.last_activity >= self._ttl_seconds
        ]
        for session_id in expired_ids:
            self._sessions.pop(session_id, None)

