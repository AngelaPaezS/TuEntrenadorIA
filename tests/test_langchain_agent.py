"""Pruebas de las herramientas y construcción del agente sin consumir Cohere."""

from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from tu_entrenador_ia.coach import CoachIA
from tu_entrenador_ia.langchain_agent import LangChainCoachAgent, _build_tools
from tu_entrenador_ia.retrieval import DocumentCorpus
from tu_entrenador_ia.settings import CohereSettings

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_DIR = PROJECT_ROOT / "documents"


class LangChainAgentTests(unittest.TestCase):
    """Verifica que LangChain use herramientas sujetas al dominio."""

    @classmethod
    def setUpClass(cls) -> None:
        """Carga una sola vez el dominio y el corpus documental."""

        cls.coach = CoachIA.from_directory(DOCUMENTS_DIR)
        cls.corpus = DocumentCorpus.build(DOCUMENTS_DIR)

    def test_tools_include_validated_routine_generator(self) -> None:
        """El agente debe contar con la única herramienta autorizada para rutinas."""

        tools = {
            current_tool.name: current_tool
            for current_tool in _build_tools(self.coach, self.corpus)
        }
        self.assertIn("generar_rutina_validada", tools)
        result = tools["generar_rutina_validada"].invoke(
            {
                "name": "Ana",
                "age": 28,
                "objective": "mejorar condicion fisica",
                "days": 2,
                "minutes": 15,
                "is_beginner": True,
                "accepted_policies": True,
            }
        )
        self.assertIn("Rutina para: Ana", result)

    def test_tool_rejects_invalid_habit_duration(self) -> None:
        """La capa LangChain no puede evadir la validación determinista."""

        tools = {
            current_tool.name: current_tool
            for current_tool in _build_tools(self.coach, self.corpus)
        }
        result = tools["generar_rutina_validada"].invoke(
            {
                "name": "Ana",
                "age": 28,
                "objective": "crear habito",
                "days": 4,
                "minutes": 30,
                "is_beginner": True,
                "accepted_policies": True,
            }
        )
        self.assertIn("tiempo máximo por sesión es de 20 minutos", result)

    def test_agent_graph_is_created_with_limits(self) -> None:
        """La construcción configura el grafo sin realizar llamadas externas."""

        fake_graph = MagicMock()
        with patch(
            "tu_entrenador_ia.langchain_agent.create_agent",
            return_value=fake_graph,
        ) as mocked_create:
            agent = LangChainCoachAgent(
                coach=self.coach,
                corpus=self.corpus,
                settings=CohereSettings(api_key="clave_falsa"),
            )
        self.assertEqual("command-a-03-2025", agent.model_name)
        self.assertEqual(len(self.corpus.documents), agent.document_count)
        self.assertEqual(4, len(mocked_create.call_args.kwargs["tools"]))
        self.assertEqual(3, len(mocked_create.call_args.kwargs["middleware"]))


if __name__ == "__main__":
    unittest.main()
