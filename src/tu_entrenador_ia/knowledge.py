"""Carga documentos, estructura ejercicios y recupera conocimiento relevante."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
from pathlib import Path
import re

from .docx_reader import BlockKind, DocumentBlock, DocumentContent, read_docx
from .models import Exercise
from .text_utils import normalize_text, tokenize

_NUMBERED_HEADING = re.compile(r"^\d+\.\s+(.+)$")


class KnowledgeError(RuntimeError):
    """Indica que las fuentes documentales están incompletas o son inconsistentes."""


@dataclass(frozen=True, slots=True)
class KnowledgeSection:
    """Fragmento autocontenido usado como unidad de búsqueda."""

    document_name: str
    title: str
    text: str


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Sección encontrada junto con su puntuación de relevancia."""

    section: KnowledgeSection
    score: float


class BM25Index:
    """Índice BM25 pequeño y en memoria, adecuado para los documentos del proyecto."""

    __slots__ = (
        "_sections",
        "_term_frequencies",
        "_document_frequencies",
        "_lengths",
        "_average_length",
    )

    def __init__(self, sections: tuple[KnowledgeSection, ...]) -> None:
        """Precalcula frecuencias una sola vez para acelerar todas las consultas."""

        self._sections = sections
        term_frequencies: list[Counter[str]] = []
        document_frequencies: Counter[str] = Counter()
        lengths: list[int] = []

        for section in sections:
            terms = tokenize(
                f"{section.document_name} {section.title} {section.text}"
            )
            frequencies = Counter(terms)
            term_frequencies.append(frequencies)
            document_frequencies.update(frequencies.keys())
            lengths.append(len(terms))

        self._term_frequencies = tuple(term_frequencies)
        self._document_frequencies = document_frequencies
        self._lengths = tuple(lengths)
        self._average_length = (
            sum(lengths) / len(lengths) if lengths else 1.0
        )

    def search(self, query: str, limit: int = 5) -> tuple[SearchResult, ...]:
        """Ordena las secciones por coincidencia BM25 con una pregunta."""

        if limit < 1:
            raise ValueError("El límite de resultados debe ser mayor que cero.")
        query_terms = tuple(dict.fromkeys(tokenize(query)))
        if not query_terms or not self._sections:
            return ()

        total_documents = len(self._sections)
        k1 = 1.5
        b = 0.75
        scored: list[SearchResult] = []
        for index, frequencies in enumerate(self._term_frequencies):
            score = 0.0
            document_length = self._lengths[index]
            for term in query_terms:
                frequency = frequencies.get(term, 0)
                if frequency == 0:
                    continue
                containing_documents = self._document_frequencies[term]
                inverse_frequency = math.log(
                    1
                    + (total_documents - containing_documents + 0.5)
                    / (containing_documents + 0.5)
                )
                denominator = frequency + k1 * (
                    1 - b + b * document_length / self._average_length
                )
                score += inverse_frequency * frequency * (k1 + 1) / denominator
            if score > 0:
                scored.append(
                    SearchResult(section=self._sections[index], score=score)
                )

        scored.sort(key=lambda result: result.score, reverse=True)
        return tuple(scored[:limit])


class KnowledgeBase:
    """Representación cargada una vez de todos los documentos del proyecto."""

    __slots__ = ("_documents", "_sections", "_index", "_exercises")

    def __init__(self, documents: tuple[DocumentContent, ...]) -> None:
        """Construye secciones, índice y catálogo a partir de documentos leídos."""

        if not documents:
            raise KnowledgeError("No se encontraron documentos DOCX.")
        self._documents = documents
        self._sections = _build_sections(documents)
        self._index = BM25Index(self._sections)
        self._exercises = _extract_exercises(documents)

    @classmethod
    def load(cls, directory: Path) -> "KnowledgeBase":
        """Lee todos los DOCX de una carpeta en orden por nombre."""

        resolved_directory = directory.resolve()
        if not resolved_directory.is_dir():
            raise KnowledgeError(
                f"No existe la carpeta de documentos: {resolved_directory}"
            )
        paths = sorted(
            (
                path
                for path in resolved_directory.iterdir()
                if path.is_file() and path.suffix.casefold() == ".docx"
            ),
            key=lambda path: path.name.casefold(),
        )
        if not paths:
            raise KnowledgeError(
                f"No hay archivos DOCX en {resolved_directory}."
            )
        return cls(tuple(read_docx(path) for path in paths))

    @property
    def documents(self) -> tuple[DocumentContent, ...]:
        """Expone los documentos cargados como una colección inmutable."""

        return self._documents

    @property
    def sections(self) -> tuple[KnowledgeSection, ...]:
        """Expone las secciones utilizadas por el buscador."""

        return self._sections

    @property
    def exercises(self) -> tuple[Exercise, ...]:
        """Devuelve el catálogo autorizado extraído de las tablas."""

        return self._exercises

    @property
    def master_prompt(self) -> str:
        """Devuelve el texto completo del documento Prompt Maestro."""

        return self._document_text_containing("prompt_maestro")

    @property
    def policies(self) -> str:
        """Devuelve el texto completo del documento de políticas."""

        return self._document_text_containing("politicas")

    def search(self, query: str, limit: int = 5) -> tuple[SearchResult, ...]:
        """Busca una pregunta en todos los documentos cargados."""

        return self._index.search(query, limit)

    def _document_text_containing(self, fragment: str) -> str:
        """Localiza un documento por una parte normalizada de su nombre."""

        normalized_fragment = normalize_text(fragment).replace(" ", "_")
        for document in self._documents:
            normalized_name = normalize_text(document.path.stem).replace(" ", "_")
            if normalized_fragment in normalized_name:
                return document.text
        raise KnowledgeError(
            f"No se encontró un documento cuyo nombre contenga {fragment!r}."
        )


def _build_sections(
    documents: tuple[DocumentContent, ...],
) -> tuple[KnowledgeSection, ...]:
    """Convierte bloques DOCX en fragmentos con el encabezado que les corresponde."""

    sections: list[KnowledgeSection] = []
    for document in documents:
        current_title = document.path.stem
        for block in document.blocks:
            if block.source_part != "word/document.xml":
                auxiliary_title = f"{current_title} ({block.source_part})"
            else:
                auxiliary_title = current_title

            if block.kind is BlockKind.PARAGRAPH and _is_heading(block):
                current_title = block.text
                continue
            if not block.text:
                continue
            sections.append(
                KnowledgeSection(
                    document_name=document.path.name,
                    title=auxiliary_title,
                    text=block.text,
                )
            )
    return tuple(sections)


def _is_heading(block: DocumentBlock) -> bool:
    """Reconoce los estilos de título utilizados por los documentos fuente."""

    normalized_style = normalize_text(block.style)
    return normalized_style == "title" or normalized_style.startswith("heading")


def _extract_exercises(
    documents: tuple[DocumentContent, ...],
) -> tuple[Exercise, ...]:
    """Convierte las tablas numeradas de la biblioteca en objetos Exercise."""

    library = next(
        (
            document
            for document in documents
            if "biblioteca_de_ejercicios"
            in normalize_text(document.path.stem).replace(" ", "_")
        ),
        None,
    )
    if library is None:
        raise KnowledgeError("Falta el documento Biblioteca de Ejercicios.")

    exercises: list[Exercise] = []
    pending_name: str | None = None
    for block in library.blocks:
        if block.source_part != "word/document.xml":
            continue
        if block.kind is BlockKind.PARAGRAPH and _is_heading(block):
            match = _NUMBERED_HEADING.match(block.text)
            pending_name = match.group(1).strip() if match else None
            continue
        if block.kind is not BlockKind.TABLE or pending_name is None:
            continue

        fields = _two_column_table(block, pending_name)
        exercises.append(
            Exercise(
                name=pending_name,
                muscle_group=_required_field(fields, "grupo muscular", pending_name),
                level=_required_field(fields, "nivel", pending_name),
                equipment=_required_field(fields, "equipo", pending_name),
                sets=_required_field(fields, "series", pending_name),
                prescription=_required_field(
                    fields, "repeticiones / tiempo", pending_name
                ),
                rest=_required_field(fields, "descanso", pending_name),
                description=_required_field(fields, "descripcion", pending_name),
            )
        )
        pending_name = None

    if not exercises:
        raise KnowledgeError(
            "La Biblioteca de Ejercicios no contiene tablas reconocibles."
        )
    duplicate_names = [
        name
        for name, count in Counter(
            normalize_text(exercise.name) for exercise in exercises
        ).items()
        if count > 1
    ]
    if duplicate_names:
        raise KnowledgeError(
            "Hay ejercicios duplicados: " + ", ".join(duplicate_names)
        )
    return tuple(exercises)


def _two_column_table(block: DocumentBlock, exercise_name: str) -> dict[str, str]:
    """Transforma una tabla de pares campo-valor en un diccionario normalizado."""

    fields: dict[str, str] = {}
    for row in block.rows:
        if len(row) < 2:
            raise KnowledgeError(
                f"La tabla de {exercise_name} tiene una fila con menos de dos celdas."
            )
        key = normalize_text(row[0])
        if key:
            fields[key] = row[1].strip()
    return fields


def _required_field(
    fields: dict[str, str], key: str, exercise_name: str
) -> str:
    """Obtiene un campo obligatorio o informa exactamente cuál falta."""

    try:
        value = fields[normalize_text(key)]
    except KeyError as exc:
        raise KnowledgeError(
            f"El ejercicio {exercise_name} no contiene el campo {key!r}."
        ) from exc
    if not value:
        raise KnowledgeError(
            f"El ejercicio {exercise_name} tiene vacío el campo {key!r}."
        )
    return value

