"""Motor determinista que transforma un perfil válido en una rutina semanal."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from .models import (
    Exercise,
    Objective,
    Routine,
    RoutineExercise,
    TrainingSession,
    UserProfile,
)
from .text_utils import normalize_text

SAFETY_RECOMMENDATIONS = (
    "Prioriza la técnica correcta antes que la velocidad.",
    "Respeta los tiempos de descanso y tus límites físicos.",
    "Mantente hidratado antes, durante y después de la sesión.",
    "Detén el ejercicio si aparece dolor intenso, mareo o dificultad para respirar.",
    "Consulta a un profesional de la salud antes de comenzar si tienes una "
    "condición médica o dudas sobre tu estado de salud.",
)


class RoutineGenerationError(RuntimeError):
    """Indica que el catálogo no permite cumplir una regla de generación."""


class ExerciseCatalog:
    """Clasifica una vez los ejercicios para seleccionarlos con bajo costo."""

    __slots__ = ("all", "by_category")

    def __init__(self, exercises: tuple[Exercise, ...]) -> None:
        """Crea grupos funcionales sin modificar los datos de los documentos."""

        if not exercises:
            raise RoutineGenerationError("El catálogo de ejercicios está vacío.")
        categories: defaultdict[str, list[Exercise]] = defaultdict(list)
        for exercise in exercises:
            for category in _categories_for(exercise):
                categories[category].append(exercise)
        self.all = exercises
        self.by_category = {
            category: tuple(items) for category, items in categories.items()
        }
        for required in {
            "cardio",
            "core",
            "lower",
            "upper",
            "mobility",
            "stretch",
        }:
            if not self.by_category.get(required):
                raise RoutineGenerationError(
                    f"El catálogo no contiene ejercicios para {required}."
                )

    def pick(
        self,
        category: str,
        offset: int,
        excluded_names: set[str],
    ) -> Exercise:
        """Elige de forma reproducible un ejercicio aún no usado en la sesión."""

        pool = self.by_category.get(category, ())
        if not pool:
            raise RoutineGenerationError(
                f"No hay ejercicios disponibles en la categoría {category}."
            )
        for step in range(len(pool)):
            candidate = pool[(offset + step) % len(pool)]
            normalized_name = normalize_text(candidate.name)
            if normalized_name not in excluded_names:
                return candidate
        raise RoutineGenerationError(
            f"No hay suficientes ejercicios distintos en la categoría {category}."
        )


class RoutineEngine:
    """Aplica reglas de objetivo, tiempo y distribución semanal."""

    __slots__ = ("_catalog",)

    def __init__(self, exercises: tuple[Exercise, ...]) -> None:
        """Prepara un catálogo reutilizable para múltiples usuarios."""

        self._catalog = ExerciseCatalog(exercises)

    def generate(self, profile: UserProfile) -> Routine:
        """Valida el perfil y produce todas las sesiones solicitadas."""

        profile.validate()
        sessions = tuple(
            self._build_session(profile, day, focus)
            for day, focus in enumerate(_weekly_focus(profile.days), start=1)
        )
        return Routine(
            profile=profile,
            sessions=sessions,
            safety_recommendations=SAFETY_RECOMMENDATIONS,
            motivational_message=(
                "¡Excelente trabajo! La constancia es la clave para alcanzar tus "
                "objetivos. ¡Empieza hoy, desde casa!"
            ),
        )

    def _build_session(
        self, profile: UserProfile, day: int, focus: str
    ) -> TrainingSession:
        """Construye calentamiento, parte principal y estiramiento de un día."""

        excluded_names: set[str] = set()
        items: list[RoutineExercise] = []
        offset = (day - 1) * 2

        warmup = self._catalog.pick("warmup", offset, excluded_names)
        _append_exercise(items, excluded_names, "Calentamiento", warmup)

        categories = _category_plan(profile, focus)
        for position, category in enumerate(categories):
            exercise = self._catalog.pick(
                category,
                offset + position,
                excluded_names,
            )
            _append_exercise(
                items,
                excluded_names,
                "Ejercicios principales",
                exercise,
            )

        stretch = self._pick_stretch(focus, offset, excluded_names)
        _append_exercise(items, excluded_names, "Estiramientos", stretch)
        return TrainingSession(day=day, focus=focus, exercises=tuple(items))

    def _pick_stretch(
        self, focus: str, offset: int, excluded_names: set[str]
    ) -> Exercise:
        """Prefiere piernas o espalda según el enfoque de la sesión."""

        stretch_pool = self._catalog.by_category["stretch"]
        preferred_word = "piernas" if "inferior" in normalize_text(focus) else "espalda"
        preferred = tuple(
            item
            for item in stretch_pool
            if preferred_word in normalize_text(item.name)
        )
        if preferred:
            candidate = preferred[offset % len(preferred)]
            if normalize_text(candidate.name) not in excluded_names:
                return candidate
        return self._catalog.pick("stretch", offset, excluded_names)


def _categories_for(exercise: Exercise) -> tuple[str, ...]:
    """Asigna categorías utilizando nombre y grupo muscular del documento."""

    name = normalize_text(exercise.name)
    group = normalize_text(exercise.muscle_group)
    categories: list[str] = []

    if name.startswith("estiramiento"):
        return ("stretch",)
    if group == "movilidad":
        categories.append("mobility")
        categories.append("warmup")
        return tuple(categories)
    if group == "cardiovascular":
        categories.append("cardio")
        if name == "marcha en el lugar":
            categories.append("warmup")
        return tuple(categories)
    if "core" in group or "abdomen" in group:
        return ("core",)
    if any(word in group for word in ("pecho", "hombros", "triceps", "espalda")):
        categories.append("upper")
    if any(
        word in group
        for word in (
            "piernas",
            "gluteos",
            "aductores",
            "isquiotibiales",
            "pantorrillas",
        )
    ):
        categories.append("lower")
    return tuple(categories)


def _weekly_focus(days: int) -> tuple[str, ...]:
    """Distribuye las sesiones conforme a las reglas documentadas por días."""

    if days == 2:
        return ("Cuerpo completo", "Cuerpo completo")
    if days == 3:
        return ("Cuerpo completo A", "Cuerpo completo B", "Cuerpo completo C")
    if days == 4:
        return (
            "Tren inferior",
            "Tren superior y core",
            "Tren inferior",
            "Tren superior y core",
        )
    if days == 5:
        return (
            "Tren inferior",
            "Tren superior y core",
            "Tren inferior",
            "Tren superior y core",
            "Movilidad y cardio ligero",
        )
    raise RoutineGenerationError("La distribución semanal solo admite de 2 a 5 días.")


def _category_plan(profile: UserProfile, focus: str) -> tuple[str, ...]:
    """Define categorías principales sin exceder el tamaño de cada sesión."""

    normalized_focus = normalize_text(focus)
    if "movilidad" in normalized_focus:
        return ("cardio", "mobility", "core")

    requested_slots = {15: 3, 20: 4, 30: 6, 45: 7}[profile.minutes]
    if profile.objective is Objective.HABIT:
        requested_slots = 3

    if "inferior" in normalized_focus:
        pattern = ("lower", "core", "cardio", "lower", "lower", "cardio", "core")
    elif "superior" in normalized_focus:
        pattern = ("upper", "core", "cardio", "upper", "core", "cardio", "upper")
    elif profile.objective is Objective.WEIGHT_LOSS:
        pattern = ("lower", "cardio", "core", "upper", "cardio", "lower", "upper")
    elif profile.objective is Objective.FITNESS:
        pattern = ("lower", "upper", "core", "cardio", "lower", "upper", "core")
    else:
        pattern = ("lower", "upper", "core")
    return pattern[:requested_slots]


def _append_exercise(
    destination: list[RoutineExercise],
    excluded_names: set[str],
    section: str,
    exercise: Exercise,
) -> None:
    """Añade un ejercicio y evita que vuelva a elegirse en la misma sesión."""

    destination.append(RoutineExercise(section=section, exercise=exercise))
    excluded_names.add(normalize_text(exercise.name))


def all_exercise_names(routine: Routine) -> Iterable[str]:
    """Recorre los nombres de una rutina; resulta útil para auditorías y pruebas."""

    for session in routine.sessions:
        for item in session.exercises:
            yield item.exercise.name

