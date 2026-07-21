"""Pruebas del límite gratuito que protege las llamadas públicas."""

import unittest

from tu_entrenador_ia.web_rate_limit import InMemoryRateLimiter


class WebRateLimiterTests(unittest.TestCase):
    """Comprueba ventana móvil, recuperación y límites de configuración."""

    def test_blocks_after_maximum_and_reports_wait(self) -> None:
        """La solicitud excedente debe indicar cuántos segundos esperar."""

        now = [0.0]
        limiter = InMemoryRateLimiter(
            max_requests=2,
            window_seconds=10,
            clock=lambda: now[0],
        )
        self.assertIsNone(limiter.retry_after("cliente"))
        now[0] = 1.0
        self.assertIsNone(limiter.retry_after("cliente"))
        now[0] = 2.0
        self.assertEqual(8, limiter.retry_after("cliente"))

    def test_allows_requests_after_window_expires(self) -> None:
        """Un cliente vuelve a disponer de capacidad al vencer la ventana."""

        now = [0.0]
        limiter = InMemoryRateLimiter(
            max_requests=1,
            window_seconds=10,
            clock=lambda: now[0],
        )
        self.assertIsNone(limiter.retry_after("cliente"))
        now[0] = 10.0
        self.assertIsNone(limiter.retry_after("cliente"))

    def test_rejects_invalid_configuration(self) -> None:
        """Los límites inválidos deben fallar antes de iniciar el servidor."""

        with self.assertRaises(ValueError):
            InMemoryRateLimiter(max_requests=0)
        with self.assertRaises(ValueError):
            InMemoryRateLimiter(window_seconds=0)
        with self.assertRaises(ValueError):
            InMemoryRateLimiter(max_clients=0)


if __name__ == "__main__":
    unittest.main()
