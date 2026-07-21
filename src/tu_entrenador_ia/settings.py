"""Configuración segura del proveedor Cohere y rutas internas del proyecto."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import dotenv_values


class ConfigurationError(RuntimeError):
    """Indica una variable ausente, inválida o una credencial rechazada."""


@dataclass(frozen=True, slots=True)
class WebSettings:
    """Dirección y puerto usados por el servidor web local o en Render."""

    host: str = "127.0.0.1"
    port: int = 8_000

    @classmethod
    def from_project(cls, project_directory: Path) -> "WebSettings":
        """Carga valores web desde `.env`, con prioridad para el entorno."""

        env_path = project_directory.resolve() / ".env"
        file_values = dotenv_values(env_path) if env_path.is_file() else {}
        host = str(
            os.environ.get("WEB_HOST", file_values.get("WEB_HOST", "127.0.0.1"))
            or ""
        ).strip()
        raw_port = str(
            os.environ.get("PORT")
            or os.environ.get("WEB_PORT")
            or file_values.get("WEB_PORT", "8000")
            or ""
        ).strip()
        if not host:
            raise ConfigurationError("WEB_HOST no puede estar vacío.")
        try:
            port = int(raw_port)
        except ValueError as exc:
            raise ConfigurationError(
                "PORT o WEB_PORT debe ser un número entero."
            ) from exc
        if not 1 <= port <= 65_535:
            raise ConfigurationError(
                "PORT o WEB_PORT debe estar entre 1 y 65535."
            )
        return cls(host=host, port=port)


@dataclass(frozen=True, slots=True)
class CohereSettings:
    """Configuración validada; la representación nunca expone la API key."""

    api_key: str = field(repr=False)
    model: str = "command-a-03-2025"
    temperature: float = 0.1
    timeout_seconds: float = 60.0
    max_retries: int = 2

    @classmethod
    def from_project(cls, project_directory: Path) -> "CohereSettings":
        """Carga `.env`, permite sobrescribir con el entorno y valida los valores."""

        env_path = project_directory.resolve() / ".env"
        file_values = dotenv_values(env_path) if env_path.is_file() else {}

        def value(name: str, default: str = "") -> str:
            """Da prioridad a variables del proceso sobre el archivo local."""

            raw_value = os.environ.get(name, file_values.get(name, default))
            return str(raw_value or "").strip()

        api_key = value("COHERE_API_KEY")
        if not api_key:
            raise ConfigurationError(
                f"Falta COHERE_API_KEY en {env_path}. Agrega la clave después "
                "del signo igual y guarda el archivo."
            )
        if api_key.casefold() in {"tu_api_key", "tu_clave_aqui", "pega_aqui"}:
            raise ConfigurationError(
                "COHERE_API_KEY todavía contiene un valor de ejemplo."
            )

        model = value("COHERE_MODEL", "command-a-03-2025")
        try:
            temperature = float(value("COHERE_TEMPERATURE", "0.1"))
            timeout_seconds = float(value("COHERE_TIMEOUT_SECONDS", "60"))
            max_retries = int(value("COHERE_MAX_RETRIES", "2"))
        except ValueError as exc:
            raise ConfigurationError(
                "La temperatura, el tiempo máximo o los reintentos no son válidos."
            ) from exc
        if not 0 <= temperature <= 1:
            raise ConfigurationError("COHERE_TEMPERATURE debe estar entre 0 y 1.")
        if timeout_seconds <= 0:
            raise ConfigurationError("COHERE_TIMEOUT_SECONDS debe ser positivo.")
        if not 0 <= max_retries <= 5:
            raise ConfigurationError("COHERE_MAX_RETRIES debe estar entre 0 y 5.")

        return cls(
            api_key=api_key,
            model=model,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )


def check_cohere_api_key(
    settings: CohereSettings,
    timeout_seconds: float = 15.0,
) -> bool:
    """Consulta el endpoint oficial de validación sin imprimir la credencial."""

    request = Request(
        "https://api.cohere.com/v1/check-api-key",
        data=b"{}",
        headers={
            "Authorization": f"Bearer {settings.api_key}",
            "Content-Type": "application/json",
            "X-Client-Name": "tu-entrenador-ia",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code in {401, 403, 498}:
            raise ConfigurationError(
                "Cohere rechazó la API key. Verifica que esté completa y activa."
            ) from exc
        raise ConfigurationError(
            f"Cohere respondió con el estado HTTP {exc.code}."
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise ConfigurationError(
            "No fue posible conectar con Cohere. Revisa tu conexión a internet."
        ) from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigurationError(
            "Cohere devolvió una respuesta que no pudo interpretarse."
        ) from exc
    return bool(payload.get("valid"))
