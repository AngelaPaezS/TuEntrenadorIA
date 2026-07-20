"""Pruebas mínimas de los comandos públicos de consola."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import unittest

from tu_entrenador_ia.cli import main

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_DIR = PROJECT_ROOT.parent


class CliTests(unittest.TestCase):
    """Comprueba códigos de salida y resultados visibles."""

    def test_inspect_command_reports_catalog(self) -> None:
        """El comando inspect debe poder ejecutarse sin interacción."""

        output = StringIO()
        with redirect_stdout(output):
            code = main(["--documents", str(DOCUMENTS_DIR), "inspect"])
        self.assertEqual(0, code)
        self.assertIn("Ejercicios autorizados: 20", output.getvalue())

    def test_complete_routine_command_is_non_interactive(self) -> None:
        """Todos los argumentos permiten integrar el programa en automatizaciones."""

        output = StringIO()
        with redirect_stdout(output):
            code = main(
                [
                    "--documents",
                    str(DOCUMENTS_DIR),
                    "routine",
                    "--name",
                    "Ana",
                    "--age",
                    "28",
                    "--objective",
                    "mejorar condicion fisica",
                    "--days",
                    "3",
                    "--minutes",
                    "20",
                    "--beginner",
                    "--accept-policies",
                ]
            )
        self.assertEqual(0, code)
        self.assertIn("Rutina para: Ana", output.getvalue())
        self.assertIn("Día 3", output.getvalue())

    def test_invalid_profile_returns_error_code(self) -> None:
        """Una edad fuera del alcance se informa sin mostrar una traza."""

        errors = StringIO()
        with redirect_stderr(errors):
            code = main(
                [
                    "--documents",
                    str(DOCUMENTS_DIR),
                    "routine",
                    "--name",
                    "Ana",
                    "--age",
                    "70",
                    "--objective",
                    "bajar de peso",
                    "--days",
                    "2",
                    "--minutes",
                    "15",
                    "--beginner",
                    "--accept-policies",
                ]
            )
        self.assertEqual(2, code)
        self.assertIn("18 a 59", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
