"""Pruebas de estructuración y búsqueda sobre la base documental."""

from pathlib import Path
import unittest

from tu_entrenador_ia.knowledge import KnowledgeBase

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_DIR = PROJECT_ROOT.parent


class KnowledgeBaseTests(unittest.TestCase):
    """Valida que el conocimiento cargado sea completo y consultable."""

    @classmethod
    def setUpClass(cls) -> None:
        """Carga los documentos una vez para todas las pruebas de esta clase."""

        cls.knowledge = KnowledgeBase.load(DOCUMENTS_DIR)

    def test_loads_six_documents_and_twenty_exercises(self) -> None:
        """La imagen no se trata como documento y las seis fuentes sí."""

        self.assertEqual(6, len(self.knowledge.documents))
        self.assertEqual(20, len(self.knowledge.exercises))

    def test_exercise_fields_come_from_table(self) -> None:
        """Los valores estructurados deben coincidir con la primera tabla."""

        march = self.knowledge.exercises[0]
        self.assertEqual("Marcha en el lugar", march.name)
        self.assertEqual("Cardiovascular", march.muscle_group)
        self.assertEqual("2 minutos", march.prescription)
        self.assertEqual("30 segundos", march.rest)

    def test_master_prompt_and_policies_are_accessible(self) -> None:
        """Las dos fuentes críticas deben poder recuperarse por su función."""

        self.assertIn("No generes una rutina", self.knowledge.master_prompt)
        self.assertIn("Responsabilidad del usuario", self.knowledge.policies)

    def test_search_returns_traceable_restrictions(self) -> None:
        """Una consulta sobre suplementos debe recuperar una restricción explícita."""

        results = self.knowledge.search(
            "¿Puede recomendar suplementos o medicamentos?", limit=3
        )
        self.assertTrue(results)
        combined = " ".join(result.section.text for result in results)
        self.assertTrue(
            "suplementos" in combined.casefold()
            or "medicamentos" in combined.casefold()
        )
        self.assertTrue(all(result.section.document_name for result in results))


if __name__ == "__main__":
    unittest.main()
