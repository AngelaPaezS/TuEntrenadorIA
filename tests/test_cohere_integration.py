"""Prueba real opcional; se omite para no consumir API en la suite normal."""

import os
from pathlib import Path
import unittest

from tu_entrenador_ia.coach import CoachIA
from tu_entrenador_ia.langchain_agent import LangChainCoachAgent
from tu_entrenador_ia.settings import CohereSettings

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_DIR = PROJECT_ROOT / "documents"


@unittest.skipUnless(
    os.environ.get("RUN_COHERE_INTEGRATION_TEST") == "1",
    "Requiere RUN_COHERE_INTEGRATION_TEST=1 y consume la API de Cohere.",
)
class CohereIntegrationTests(unittest.TestCase):
    """Comprueba modelo y tool calling contra el servicio real."""

    def test_agent_can_call_validated_routine_tool(self) -> None:
        """Una solicitud completa debe regresar la rutina del motor local."""

        coach = CoachIA.from_directory(DOCUMENTS_DIR)
        settings = CohereSettings.from_project(PROJECT_ROOT)
        agent = LangChainCoachAgent.from_project(
            coach=coach,
            documents_directory=DOCUMENTS_DIR,
            project_directory=PROJECT_ROOT,
            settings=settings,
        )
        response = agent.ask(
            "Genera mi rutina. Me llamo Ana, tengo 28 años, soy principiante, "
            "mi objetivo es mejorar condición física, entrenaré 2 días, "
            "15 minutos por sesión y acepto expresamente las políticas."
        )
        self.assertIn("Rutina para: Ana", response)


if __name__ == "__main__":
    unittest.main()
