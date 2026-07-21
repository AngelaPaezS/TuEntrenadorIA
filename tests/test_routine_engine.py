"""Pruebas combinatorias del motor determinista de rutinas."""

from pathlib import Path
import unittest

from tu_entrenador_ia.knowledge import KnowledgeBase
from tu_entrenador_ia.models import Objective, UserProfile
from tu_entrenador_ia.routine_engine import RoutineEngine, all_exercise_names
from tu_entrenador_ia.text_utils import normalize_text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_DIR = PROJECT_ROOT / "documents"


class RoutineEngineTests(unittest.TestCase):
    """Verifica reglas, distribución y pertenencia al catálogo autorizado."""

    @classmethod
    def setUpClass(cls) -> None:
        """Carga catálogo y motor una sola vez para acelerar la suite."""

        knowledge = KnowledgeBase.load(DOCUMENTS_DIR)
        cls.catalog_names = {
            normalize_text(exercise.name) for exercise in knowledge.exercises
        }
        cls.engine = RoutineEngine(knowledge.exercises)

    def test_supported_combinations_generate_valid_sessions(self) -> None:
        """Todas las combinaciones admitidas deben producir una rutina completa."""

        combinations = [
            (objective, days, minutes)
            for objective in (Objective.WEIGHT_LOSS, Objective.FITNESS)
            for days in (2, 3, 4, 5)
            for minutes in (15, 20, 30, 45)
        ]
        combinations.extend(
            (Objective.HABIT, days, minutes)
            for days in (2, 3, 4, 5)
            for minutes in (15, 20)
        )

        for objective, days, minutes in combinations:
            with self.subTest(objective=objective, days=days, minutes=minutes):
                profile = UserProfile(
                    name="Prueba",
                    age=30,
                    objective=objective,
                    days=days,
                    minutes=minutes,
                    is_beginner=True,
                    accepted_policies=True,
                )
                routine = self.engine.generate(profile)
                self.assertEqual(days, len(routine.sessions))
                self.assertGreaterEqual(len(routine.safety_recommendations), 5)
                for session in routine.sessions:
                    self.assertEqual(
                        "Calentamiento", session.exercises[0].section
                    )
                    self.assertEqual(
                        "Estiramientos", session.exercises[-1].section
                    )
                    names = [
                        normalize_text(item.exercise.name)
                        for item in session.exercises
                    ]
                    self.assertEqual(len(names), len(set(names)))
                    self.assertTrue(set(names).issubset(self.catalog_names))

    def test_fifth_day_is_light_mobility_and_cardio(self) -> None:
        """La distribución de cinco días aplica la regla especial del manual."""

        profile = UserProfile(
            name="Prueba",
            age=25,
            objective=Objective.FITNESS,
            days=5,
            minutes=45,
            is_beginner=True,
            accepted_policies=True,
        )
        routine = self.engine.generate(profile)
        fifth_session = routine.sessions[4]
        self.assertEqual("Movilidad y cardio ligero", fifth_session.focus)
        self.assertEqual(5, len(fifth_session.exercises))

    def test_every_generated_name_belongs_to_catalog(self) -> None:
        """El generador nunca puede inventar un ejercicio."""

        profile = UserProfile(
            name="Prueba",
            age=40,
            objective=Objective.WEIGHT_LOSS,
            days=4,
            minutes=30,
            is_beginner=True,
            accepted_policies=True,
        )
        routine = self.engine.generate(profile)
        self.assertTrue(
            all(
                normalize_text(name) in self.catalog_names
                for name in all_exercise_names(routine)
            )
        )


if __name__ == "__main__":
    unittest.main()
