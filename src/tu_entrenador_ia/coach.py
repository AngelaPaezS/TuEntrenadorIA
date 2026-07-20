"""Fachada del agente: simplifica carga, consulta y generación de rutinas."""

from __future__ import annotations

from pathlib import Path

from .knowledge import KnowledgeBase, SearchResult
from .models import Objective, Routine, UserProfile
from .routine_engine import RoutineEngine


class CoachIA:
    """Punto de entrada de alto nivel para usar todas las capacidades del programa."""

    __slots__ = ("knowledge", "_routine_engine")

    def __init__(self, knowledge: KnowledgeBase) -> None:
        """Recibe conocimiento ya cargado y prepara el motor una sola vez."""

        self.knowledge = knowledge
        self._routine_engine = RoutineEngine(knowledge.exercises)

    @classmethod
    def from_directory(cls, directory: Path) -> "CoachIA":
        """Crea el agente leyendo los documentos de la carpeta indicada."""

        return cls(KnowledgeBase.load(directory))

    def search(self, question: str, limit: int = 5) -> tuple[SearchResult, ...]:
        """Recupera los fragmentos documentales más relevantes para una pregunta."""

        return self.knowledge.search(question, limit)

    def create_routine(
        self,
        *,
        name: str,
        age: int,
        objective: str | Objective,
        days: int,
        minutes: int,
        is_beginner: bool,
        accepted_policies: bool,
    ) -> Routine:
        """Valida datos obligatorios y genera una rutina semanal completa."""

        parsed_objective = (
            objective if isinstance(objective, Objective) else Objective.parse(objective)
        )
        profile = UserProfile(
            name=name.strip(),
            age=age,
            objective=parsed_objective,
            days=days,
            minutes=minutes,
            is_beginner=is_beginner,
            accepted_policies=accepted_policies,
        )
        return self._routine_engine.generate(profile)

    def summary(self) -> str:
        """Resume qué pudo leer y estructurar el agente."""

        paragraph_count = sum(
            1
            for document in self.knowledge.documents
            for block in document.blocks
            if block.kind.value == "paragraph"
        )
        table_count = sum(
            1
            for document in self.knowledge.documents
            for block in document.blocks
            if block.kind.value == "table"
        )
        return (
            f"Documentos leídos: {len(self.knowledge.documents)}\n"
            f"Párrafos procesados: {paragraph_count}\n"
            f"Tablas procesadas: {table_count}\n"
            f"Secciones indexadas: {len(self.knowledge.sections)}\n"
            f"Ejercicios autorizados: {len(self.knowledge.exercises)}"
        )


def format_search_results(results: tuple[SearchResult, ...]) -> str:
    """Presenta resultados con fuente y un fragmento de longitud controlada."""

    if not results:
        return "No encontré información relacionada en los documentos."

    lines: list[str] = []
    for position, result in enumerate(results, start=1):
        compact_text = " ".join(result.section.text.split())
        excerpt = (
            compact_text
            if len(compact_text) <= 500
            else compact_text[:497].rstrip() + "..."
        )
        lines.extend(
            (
                f"{position}. {result.section.title}",
                f"   Fuente: {result.section.document_name}",
                f"   {excerpt}",
            )
        )
    return "\n".join(lines)


def format_routine(routine: Routine) -> str:
    """Convierte una rutina validada al formato solicitado por el Prompt Maestro."""

    profile = routine.profile
    lines = [
        f"Rutina para: {profile.name}",
        f"Objetivo del entrenamiento: {profile.objective.value}",
        f"Duración por sesión: {profile.minutes} minutos",
        f"Días por semana: {profile.days}",
        "",
    ]
    for session in routine.sessions:
        lines.append(f"Día {session.day} — {session.focus}")
        current_section = ""
        for item in session.exercises:
            if item.section != current_section:
                current_section = item.section
                lines.append(f"  {current_section}:")
            exercise = item.exercise
            lines.append(
                f"    - {exercise.name}: {exercise.sets} serie(s), "
                f"{exercise.prescription}; descanso: {exercise.rest}."
            )
            lines.append(f"      Cómo hacerlo: {exercise.description}")
        lines.append("")

    lines.append("Recomendaciones finales:")
    lines.extend(f"  - {recommendation}" for recommendation in routine.safety_recommendations)
    lines.extend(("", routine.motivational_message))
    return "\n".join(lines)

