"""Límite ligero en memoria para proteger las llamadas públicas a Cohere."""

from __future__ import annotations

from collections import OrderedDict, deque
from collections.abc import Callable
from math import ceil
from threading import Lock
from time import monotonic


class InMemoryRateLimiter:
    """Limita mensajes por cliente sin servicios ni dependencias adicionales."""

    __slots__ = (
        "_clock",
        "_lock",
        "_max_clients",
        "_max_requests",
        "_requests",
        "_window_seconds",
    )

    def __init__(
        self,
        *,
        max_requests: int = 10,
        window_seconds: float = 60.0,
        max_clients: int = 10_000,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        """Configura una ventana móvil y limita también el uso de memoria."""

        if max_requests < 1:
            raise ValueError("Debe permitirse al menos una solicitud.")
        if window_seconds <= 0:
            raise ValueError("La ventana de tiempo debe ser positiva.")
        if max_clients < 1:
            raise ValueError("Debe permitirse al menos un cliente.")

        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._max_clients = max_clients
        self._clock = clock
        self._lock = Lock()
        self._requests: OrderedDict[str, deque[float]] = OrderedDict()

    def retry_after(self, client_id: str) -> int | None:
        """Registra una solicitud o devuelve los segundos que debe esperar."""

        identifier = client_id.strip() or "desconocido"
        now = self._clock()
        cutoff = now - self._window_seconds

        with self._lock:
            self._remove_inactive_clients(cutoff)
            history = self._requests.get(identifier)
            if history is None:
                if len(self._requests) >= self._max_clients:
                    self._requests.popitem(last=False)
                history = deque()
                self._requests[identifier] = history
            else:
                while history and history[0] <= cutoff:
                    history.popleft()

            self._requests.move_to_end(identifier)
            if len(history) >= self._max_requests:
                return max(1, ceil(history[0] + self._window_seconds - now))

            history.append(now)
            return None

    def _remove_inactive_clients(self, cutoff: float) -> None:
        """Descarta clientes antiguos empezando por el menos reciente."""

        while self._requests:
            identifier, history = next(iter(self._requests.items()))
            while history and history[0] <= cutoff:
                history.popleft()
            if history:
                return
            self._requests.pop(identifier, None)
