"""Pruebas del aislamiento, caducidad y reinicio de sesiones web."""

from __future__ import annotations

import unittest
from uuid import UUID

from tu_entrenador_ia.web_sessions import WebSessionStore


class _FakeAgent:
    """Agente mínimo que permite observar el historial de cada sesión."""

    def __init__(self) -> None:
        """Inicia una conversación vacía."""

        self.messages: list[str] = []

    def ask(self, message: str) -> str:
        """Guarda el mensaje y devuelve el número de turno."""

        self.messages.append(message)
        return f"turno {len(self.messages)}: {message}"

    def clear_history(self) -> None:
        """Elimina los mensajes simulados."""

        self.messages.clear()


class WebSessionStoreTests(unittest.TestCase):
    """Valida que ningún navegador comparta memoria con otro."""

    def test_same_session_keeps_history(self) -> None:
        """Un identificador vigente debe recuperar el mismo agente."""

        store = WebSessionStore(_FakeAgent)
        session_id, first = store.ask(None, "hola")
        repeated_id, second = store.ask(session_id, "segunda")
        self.assertEqual(session_id, repeated_id)
        self.assertEqual("turno 1: hola", first)
        self.assertEqual("turno 2: segunda", second)

    def test_different_sessions_are_isolated(self) -> None:
        """Dos sesiones nuevas deben comenzar siempre en su primer turno."""

        store = WebSessionStore(_FakeAgent)
        first_id, _ = store.ask(None, "uno")
        second_id, answer = store.ask(None, "dos")
        self.assertNotEqual(first_id, second_id)
        self.assertEqual("turno 1: dos", answer)

    def test_reset_removes_history(self) -> None:
        """Reiniciar debe invalidar el identificador anterior."""

        store = WebSessionStore(_FakeAgent)
        session_id, _ = store.ask(None, "hola")
        self.assertTrue(store.reset(session_id))
        self.assertFalse(store.reset(session_id))
        new_id, answer = store.ask(session_id, "nuevo")
        self.assertNotEqual(session_id, new_id)
        self.assertEqual("turno 1: nuevo", answer)

    def test_expired_session_is_replaced(self) -> None:
        """Una sesión inactiva no debe conservar datos indefinidamente."""

        current_time = [0.0]
        store = WebSessionStore(
            _FakeAgent,
            ttl_seconds=10,
            clock=lambda: current_time[0],
        )
        session_id, _ = store.ask(None, "hola")
        current_time[0] = 11.0
        replacement_id, answer = store.ask(session_id, "regreso")
        self.assertNotEqual(session_id, replacement_id)
        self.assertEqual("turno 1: regreso", answer)

    def test_unknown_uuid_creates_safe_new_session(self) -> None:
        """Un UUID válido pero desconocido no puede acceder a otra sesión."""

        store = WebSessionStore(_FakeAgent)
        requested = UUID("12345678-1234-5678-1234-567812345678")
        created, answer = store.ask(requested, "hola")
        self.assertNotEqual(requested, created)
        self.assertEqual("turno 1: hola", answer)


if __name__ == "__main__":
    unittest.main()

