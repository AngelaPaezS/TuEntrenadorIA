"""Pruebas de configuración sin leer ni enviar la credencial real."""

from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from tu_entrenador_ia.settings import (
    CohereSettings,
    ConfigurationError,
    WebSettings,
    check_cohere_api_key,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CohereSettingsTests(unittest.TestCase):
    """Valida carga, protección y verificación simulada de la API key."""

    def setUp(self) -> None:
        """Crea una carpeta temporal controlada por el proyecto."""

        self.directory = PROJECT_ROOT / ".tmp" / "settings_tests"
        self.directory.mkdir(parents=True, exist_ok=True)

    def test_loads_env_without_exposing_key_in_repr(self) -> None:
        """La configuración debe ocultar la credencial al representarse."""

        secret = "clave_de_prueba_no_real"
        (self.directory / ".env").write_text(
            f"COHERE_API_KEY={secret}\nCOHERE_MODEL=modelo-prueba\n",
            encoding="utf-8",
        )
        settings = CohereSettings.from_project(self.directory)
        self.assertEqual("modelo-prueba", settings.model)
        self.assertNotIn(secret, repr(settings))

    def test_missing_key_has_clear_error(self) -> None:
        """Un archivo sin clave debe explicar cómo corregirlo."""

        (self.directory / ".env").write_text(
            "COHERE_API_KEY=\n",
            encoding="utf-8",
        )
        with self.assertRaises(ConfigurationError) as context:
            CohereSettings.from_project(self.directory)
        self.assertIn("Falta COHERE_API_KEY", str(context.exception))

    def test_online_check_is_mocked_and_never_logs_key(self) -> None:
        """La respuesta válida se interpreta sin una llamada de red real."""

        settings = CohereSettings(api_key="secreto_no_real")
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"valid": true}'
        with patch(
            "tu_entrenador_ia.settings.urlopen",
            return_value=response,
        ) as mocked_urlopen:
            self.assertTrue(check_cohere_api_key(settings))
        request = mocked_urlopen.call_args.args[0]
        self.assertNotIn("secreto_no_real", request.full_url)

    def test_web_settings_have_safe_local_defaults(self) -> None:
        """Sin valores explícitos, el servidor solo debe escuchar localmente."""

        (self.directory / ".env").write_text("", encoding="utf-8")
        settings = WebSettings.from_project(self.directory)
        self.assertEqual("127.0.0.1", settings.host)
        self.assertEqual(8_000, settings.port)


if __name__ == "__main__":
    unittest.main()
