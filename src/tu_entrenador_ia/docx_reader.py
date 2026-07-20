"""Lector DOCX rápido basado únicamente en ZIP y XML de la biblioteca estándar."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from zipfile import BadZipFile, ZipFile
import xml.etree.ElementTree as ElementTree

WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{WORD_NAMESPACE}}}"
MAX_ARCHIVE_SIZE = 50 * 1024 * 1024
MAX_XML_SIZE = 10 * 1024 * 1024


class DocumentReadError(RuntimeError):
    """Explica por qué un archivo DOCX no pudo procesarse."""


class BlockKind(str, Enum):
    """Tipos de contenido que pueden aparecer dentro de un DOCX."""

    PARAGRAPH = "paragraph"
    TABLE = "table"


@dataclass(frozen=True, slots=True)
class DocumentBlock:
    """Bloque de texto o tabla conservado en el orden original."""

    kind: BlockKind
    text: str
    style: str = ""
    rows: tuple[tuple[str, ...], ...] = ()
    source_part: str = "word/document.xml"


@dataclass(frozen=True, slots=True)
class DocumentContent:
    """Contenido completo y normalizado de un documento Word."""

    path: Path
    blocks: tuple[DocumentBlock, ...]

    @property
    def text(self) -> str:
        """Une párrafos y tablas en texto legible para búsquedas y contexto."""

        return "\n".join(block.text for block in self.blocks if block.text)


def read_docx(path: Path) -> DocumentContent:
    """Lee cuerpo, encabezados, pies y notas de un DOCX sin extraerlo al disco."""

    resolved_path = path.resolve()
    if not resolved_path.is_file():
        raise DocumentReadError(f"No existe el documento: {resolved_path}")
    if resolved_path.suffix.casefold() != ".docx":
        raise DocumentReadError(f"El archivo no es DOCX: {resolved_path.name}")

    try:
        with ZipFile(resolved_path) as archive:
            _validate_archive(archive, resolved_path.name)
            names = set(archive.namelist())
            if "word/document.xml" not in names:
                raise DocumentReadError(
                    f"{resolved_path.name} no contiene word/document.xml."
                )

            part_names = ["word/document.xml"]
            part_names.extend(
                sorted(
                    name
                    for name in names
                    if _is_supported_auxiliary_part(name)
                )
            )
            blocks: list[DocumentBlock] = []
            for part_name in part_names:
                xml_bytes = archive.read(part_name)
                blocks.extend(_read_xml_part(xml_bytes, part_name))
    except BadZipFile as exc:
        raise DocumentReadError(
            f"{resolved_path.name} no es un DOCX válido o está dañado."
        ) from exc
    except ElementTree.ParseError as exc:
        raise DocumentReadError(
            f"{resolved_path.name} contiene XML inválido: {exc}."
        ) from exc

    return DocumentContent(path=resolved_path, blocks=tuple(blocks))


def _validate_archive(archive: ZipFile, document_name: str) -> None:
    """Limita tamaños descomprimidos para evitar archivos inesperadamente grandes."""

    total_size = sum(item.file_size for item in archive.infolist())
    if total_size > MAX_ARCHIVE_SIZE:
        raise DocumentReadError(
            f"{document_name} supera el límite descomprimido de "
            f"{MAX_ARCHIVE_SIZE // (1024 * 1024)} MB."
        )
    for item in archive.infolist():
        if item.filename.endswith(".xml") and item.file_size > MAX_XML_SIZE:
            raise DocumentReadError(
                f"La parte {item.filename} supera el límite XML permitido."
            )


def _is_supported_auxiliary_part(name: str) -> bool:
    """Indica si una parte Word adicional puede contener texto útil."""

    if not name.startswith("word/") or not name.endswith(".xml"):
        return False
    filename = name.rsplit("/", 1)[-1]
    return (
        filename.startswith("header")
        or filename.startswith("footer")
        or filename in {"footnotes.xml", "endnotes.xml", "comments.xml"}
    )


def _read_xml_part(xml_bytes: bytes, part_name: str) -> list[DocumentBlock]:
    """Convierte una parte XML de Word en bloques ordenados."""

    root = ElementTree.fromstring(xml_bytes)
    container = root.find(f"{W}body") if part_name == "word/document.xml" else root
    if container is None:
        return []

    blocks: list[DocumentBlock] = []
    for child in container:
        if child.tag == f"{W}p":
            text = _node_text(child)
            if text:
                blocks.append(
                    DocumentBlock(
                        kind=BlockKind.PARAGRAPH,
                        text=text,
                        style=_paragraph_style(child),
                        source_part=part_name,
                    )
                )
        elif child.tag == f"{W}tbl":
            rows = _table_rows(child)
            if rows:
                readable_text = "\n".join(" | ".join(row) for row in rows)
                blocks.append(
                    DocumentBlock(
                        kind=BlockKind.TABLE,
                        text=readable_text,
                        rows=rows,
                        source_part=part_name,
                    )
                )
    return blocks


def _node_text(node: ElementTree.Element) -> str:
    """Extrae texto, tabuladores y saltos conservando su orden XML."""

    parts: list[str] = []
    for element in node.iter():
        if element.tag == f"{W}t" and element.text:
            parts.append(element.text)
        elif element.tag == f"{W}tab":
            parts.append("\t")
        elif element.tag in {f"{W}br", f"{W}cr"}:
            parts.append("\n")
    return "".join(parts).strip()


def _paragraph_style(paragraph: ElementTree.Element) -> str:
    """Obtiene el nombre interno del estilo de un párrafo, si existe."""

    properties = paragraph.find(f"{W}pPr")
    if properties is None:
        return ""
    style = properties.find(f"{W}pStyle")
    if style is None:
        return ""
    return style.get(f"{W}val", "")


def _table_rows(table: ElementTree.Element) -> tuple[tuple[str, ...], ...]:
    """Convierte las filas y celdas de Word en tuplas inmutables."""

    rows: list[tuple[str, ...]] = []
    for row in table.findall(f"{W}tr"):
        cells: list[str] = []
        for cell in row.findall(f"{W}tc"):
            paragraph_texts = [
                _node_text(paragraph)
                for paragraph in cell.findall(f".//{W}p")
            ]
            cells.append("\n".join(text for text in paragraph_texts if text))
        rows.append(tuple(cells))
    return tuple(rows)

