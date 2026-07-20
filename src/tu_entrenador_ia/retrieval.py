"""Índice documental local con fragmentación LangChain, BM25 y caché segura."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .document_loaders import MultiFormatDocumentLoader
from .text_utils import tokenize

CACHE_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """Fragmento recuperado con su relevancia y metadatos de origen."""

    document: Document
    score: float


class DocumentCorpus:
    """Colección fragmentada que evita llamadas de embeddings y búsquedas remotas."""

    __slots__ = (
        "documents",
        "_term_frequencies",
        "_document_frequencies",
        "_lengths",
        "_average_length",
    )

    def __init__(self, documents: list[Document]) -> None:
        """Precalcula las frecuencias BM25 una sola vez por carga."""

        self.documents = tuple(documents)
        term_frequencies: list[Counter[str]] = []
        document_frequencies: Counter[str] = Counter()
        lengths: list[int] = []
        for document in documents:
            terms = tokenize(
                f"{document.metadata.get('filename', '')} {document.page_content}"
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

    @classmethod
    def build(
        cls,
        documents_directory: Path,
        cache_path: Path | None = None,
    ) -> "DocumentCorpus":
        """Carga desde caché válida o procesa nuevamente todos los archivos."""

        loader = MultiFormatDocumentLoader(documents_directory)
        files = loader.source_files()
        manifest = _build_manifest(files)
        cached_documents = (
            _read_cache(cache_path, manifest) if cache_path is not None else None
        )
        if cached_documents is not None:
            return cls(cached_documents)

        raw_documents = loader.load()
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1_000,
            chunk_overlap=150,
            add_start_index=True,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = splitter.split_documents(raw_documents)
        if cache_path is not None:
            _write_cache(cache_path, manifest, chunks)
        return cls(chunks)

    def search(self, query: str, limit: int = 5) -> tuple[RetrievalResult, ...]:
        """Ordena fragmentos por relevancia léxica usando BM25."""

        if limit < 1:
            raise ValueError("El límite de búsqueda debe ser mayor que cero.")
        query_terms = tuple(dict.fromkeys(tokenize(query)))
        if not query_terms or not self.documents:
            return ()

        total_documents = len(self.documents)
        k1 = 1.5
        b = 0.75
        results: list[RetrievalResult] = []
        for index, frequencies in enumerate(self._term_frequencies):
            score = 0.0
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
                    1
                    - b
                    + b * self._lengths[index] / self._average_length
                )
                score += inverse_frequency * frequency * (k1 + 1) / denominator
            if score > 0:
                results.append(
                    RetrievalResult(document=self.documents[index], score=score)
                )

        results.sort(key=lambda result: result.score, reverse=True)
        return tuple(results[:limit])


def format_retrieval_results(
    results: tuple[RetrievalResult, ...],
) -> str:
    """Prepara contexto trazable para una herramienta del agente."""

    if not results:
        return "No se encontró información relacionada en la base documental."
    parts: list[str] = []
    for position, result in enumerate(results, start=1):
        metadata = result.document.metadata
        location = _format_location(metadata)
        parts.append(
            f"[Fuente {position}: {metadata.get('filename', 'desconocida')}"
            f"{location}]\n{result.document.page_content}"
        )
    return "\n\n".join(parts)


def _format_location(metadata: dict[str, Any]) -> str:
    """Describe página, hoja o diapositiva cuando el lector la conoce."""

    if "page" in metadata:
        return f", página {metadata['page']}"
    if "sheet" in metadata:
        return f", hoja {metadata['sheet']}"
    if "slide" in metadata:
        return f", diapositiva {metadata['slide']}"
    return ""


def _build_manifest(files: tuple[Path, ...]) -> list[dict[str, Any]]:
    """Calcula una huella económica basada en ruta, tamaño y modificación."""

    return [
        {
            "path": str(path.resolve()),
            "size": path.stat().st_size,
            "modified_ns": path.stat().st_mtime_ns,
        }
        for path in files
    ]


def _read_cache(
    cache_path: Path,
    expected_manifest: list[dict[str, Any]],
) -> list[Document] | None:
    """Recupera fragmentos solo si esquema y archivos siguen sin cambios."""

    if not cache_path.is_file():
        return None
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        if payload.get("schema") != CACHE_SCHEMA_VERSION:
            return None
        if payload.get("manifest") != expected_manifest:
            return None
        return [
            Document(
                page_content=item["page_content"],
                metadata=item["metadata"],
            )
            for item in payload["documents"]
        ]
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _write_cache(
    cache_path: Path,
    manifest: list[dict[str, Any]],
    documents: list[Document],
) -> None:
    """Escribe caché de forma atómica para no dejar archivos parciales."""

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
    payload = {
        "schema": CACHE_SCHEMA_VERSION,
        "manifest": manifest,
        "documents": [
            {
                "page_content": document.page_content,
                "metadata": document.metadata,
            }
            for document in documents
        ],
    }
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    temporary_path.replace(cache_path)

