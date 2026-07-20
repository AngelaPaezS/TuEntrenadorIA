"""Pruebas del lector DOCX usando los documentos reales del proyecto."""

from pathlib import Path
import unittest

from tu_entrenador_ia.docx_reader import BlockKind, read_docx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_DIR = PROJECT_ROOT.parent


class DocxReaderTests(unittest.TestCase):
    """Comprueba que párrafos y tablas se conservan correctamente."""

    def test_reads_master_prompt_text(self) -> None:
        """El Prompt Maestro debe incluir el saludo y sus restricciones."""

        document = read_docx(DOCUMENTS_DIR / "7. Prompt_Maestro_Coach_IA.docx")
        self.assertIn("Eres Coach IA", document.text)
        self.assertIn("No debes:", document.text)
        self.assertIn("¡Hola!", document.text)

    def test_reads_all_exercise_tables(self) -> None:
        """La biblioteca debe exponer exactamente sus veinte tablas."""

        document = read_docx(
            DOCUMENTS_DIR / "5. Biblioteca_de_Ejercicios_Coach_IA.docx"
        )
        tables = [
            block for block in document.blocks if block.kind is BlockKind.TABLE
        ]
        self.assertEqual(20, len(tables))
        self.assertEqual(("Grupo muscular", "Cardiovascular"), tables[0].rows[0])


if __name__ == "__main__":
    unittest.main()
