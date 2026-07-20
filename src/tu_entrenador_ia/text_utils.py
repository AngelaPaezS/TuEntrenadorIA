"""Utilidades pequeñas para comparar y buscar texto en español."""

from __future__ import annotations

import re
import unicodedata

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def normalize_text(value: str) -> str:
    """Devuelve texto en minúsculas, sin acentos y con espacios uniformes."""

    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    lowered = without_accents.casefold()
    return " ".join(lowered.split())


def tokenize(value: str) -> tuple[str, ...]:
    """Divide texto normalizado en términos aptos para el índice de búsqueda."""

    return tuple(_TOKEN_PATTERN.findall(normalize_text(value)))

