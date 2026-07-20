"""Pruebas de normalización y validación de los datos del usuario."""

import unittest

from tu_entrenador_ia.models import (
    DomainValidationError,
    Objective,
    UserProfile,
)


class ModelTests(unittest.TestCase):
    """Cubre límites de edad, nivel, políticas y objetivos."""

    def test_objective_accepts_text_without_accents(self) -> None:
        """La consola debe ser tolerante a la escritura sin acentos."""

        self.assertIs(
            Objective.FITNESS,
            Objective.parse("mejorar condicion fisica"),
        )

    def test_age_boundaries_are_inclusive(self) -> None:
        """Las edades 18 y 59 siguen la decisión funcional registrada."""

        for age in (18, 59):
            profile = UserProfile(
                name="Persona",
                age=age,
                objective=Objective.WEIGHT_LOSS,
                days=2,
                minutes=15,
                is_beginner=True,
                accepted_policies=True,
            )
            profile.validate()

    def test_collects_multiple_validation_errors(self) -> None:
        """El usuario debe recibir todos los problemas en una sola respuesta."""

        profile = UserProfile(
            name="",
            age=60,
            objective=Objective.FITNESS,
            days=1,
            minutes=10,
            is_beginner=False,
            accepted_policies=False,
        )
        with self.assertRaises(DomainValidationError) as context:
            profile.validate()
        self.assertGreaterEqual(len(context.exception.messages), 6)

    def test_habit_rejects_long_sessions(self) -> None:
        """Crear el hábito respeta el límite documentado de veinte minutos."""

        profile = UserProfile(
            name="Persona",
            age=30,
            objective=Objective.HABIT,
            days=3,
            minutes=30,
            is_beginner=True,
            accepted_policies=True,
        )
        with self.assertRaises(DomainValidationError) as context:
            profile.validate()
        self.assertIn(
            "tiempo máximo por sesión es de 20 minutos",
            str(context.exception),
        )


if __name__ == "__main__":
    unittest.main()
