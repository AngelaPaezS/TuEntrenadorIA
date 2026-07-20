"""Componentes públicos de Tu Entrenador IA.

El paquete mantiene separadas la lectura documental, la recuperación de
conocimiento y la generación de rutinas para que cada parte pueda probarse y
reemplazarse de manera independiente.
"""

from .coach import CoachIA
from .langchain_agent import LangChainCoachAgent
from .knowledge import KnowledgeBase
from .models import Objective, Routine, UserProfile

__all__ = [
    "CoachIA",
    "KnowledgeBase",
    "LangChainCoachAgent",
    "Objective",
    "Routine",
    "UserProfile",
]
__version__ = "0.3.0"
