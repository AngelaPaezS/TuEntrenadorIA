"""Modelos inmutables y validaciones del dominio de entrenamiento."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .text_utils import normalize_text


class DomainValidationError(ValueError):
    """Indica que uno o más datos están fuera del alcance de Coach IA."""

    def __init__(self, messages: list[str] | tuple[str, ...]) -> None:
        """Guarda todos los errores para corregirlos en una sola interacción."""

        self.messages = tuple(messages)
        super().__init__(" ".join(self.messages))


class Objective(str, Enum):
    """Objetivos autorizados por el Prompt Maestro."""

    WEIGHT_LOSS = "Bajar de peso"
    FITNESS = "Mejorar condición física"
    HABIT = "Crear el hábito del ejercicio"

    @classmethod
    def parse(cls, value: str) -> "Objective":
        """Convierte variantes sencillas del usuario en un objetivo válido."""

        normalized = normalize_text(value)
        aliases = {
            "bajar de peso": cls.WEIGHT_LOSS,
            "perder peso": cls.WEIGHT_LOSS,
            "mejorar condicion fisica": cls.FITNESS,
            "condicion fisica": cls.FITNESS,
            "crear el habito del ejercicio": cls.HABIT,
            "crear habito": cls.HABIT,
            "habito": cls.HABIT,
        }
        try:
            return aliases[normalized]
        except KeyError as exc:
            allowed = ", ".join(item.value for item in cls)
            raise DomainValidationError(
                [f"Objetivo no válido. Opciones permitidas: {allowed}."]
            ) from exc


@dataclass(frozen=True, slots=True)
class Exercise:
    """Ejercicio extraído de una tabla de la Biblioteca de Ejercicios."""

    name: str
    muscle_group: str
    level: str
    equipment: str
    sets: str
    prescription: str
    rest: str
    description: str


@dataclass(frozen=True, slots=True)
class UserProfile:
    """Datos obligatorios que el Prompt Maestro solicita antes de una rutina."""

    name: str
    age: int
    objective: Objective
    days: int
    minutes: int
    is_beginner: bool
    accepted_policies: bool

    def validate(self) -> None:
        """Valida todos los límites documentados y reúne los errores encontrados."""

        errors: list[str] = []
        if not self.name.strip():
            errors.append("El nombre es obligatorio.")
        if not 18 <= self.age <= 59:
            errors.append("Coach IA solo admite personas de 18 a 59 años.")
        if self.days not in {2, 3, 4, 5}:
            errors.append("Los días disponibles deben ser 2, 3, 4 o 5.")
        if self.minutes not in {15, 20, 30, 45}:
            errors.append("La duración debe ser 15, 20, 30 o 45 minutos.")
        if not self.is_beginner:
            errors.append("Coach IA está limitado al nivel principiante.")
        if not self.accepted_policies:
            errors.append("Debes aceptar las políticas antes de generar una rutina.")
        if self.objective is Objective.HABIT and self.minutes not in {15, 20}:
            errors.append(
                "Para crear el hábito, el tiempo máximo por sesión es de 20 "
                "minutos. Selecciona una duración de 15 o 20 minutos."
            )
        if errors:
            raise DomainValidationError(errors)


@dataclass(frozen=True, slots=True)
class RoutineExercise:
    """Ejercicio seleccionado y la sección en la que debe presentarse."""

    section: str
    exercise: Exercise


@dataclass(frozen=True, slots=True)
class TrainingSession:
    """Sesión completa asignada a un día de entrenamiento."""

    day: int
    focus: str
    exercises: tuple[RoutineExercise, ...]


@dataclass(frozen=True, slots=True)
class Routine:
    """Resultado validado que Coach IA entrega al usuario."""

    profile: UserProfile
    sessions: tuple[TrainingSession, ...]
    safety_recommendations: tuple[str, ...]
    motivational_message: str
