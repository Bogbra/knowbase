"""Text extraction and chunking for document ingestion."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_SUPPORTED_MIME_TYPES = frozenset(
    {
        "text/plain",
        "text/markdown",
        "text/csv",
        "text/html",
        "application/pdf",
        "application/json",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
        "application/vnd.ms-excel",  # .xls
    }
)


def is_supported(mime_type: str) -> bool:
    return mime_type.split(";")[0].strip() in _SUPPORTED_MIME_TYPES


def extract_text(data: bytes, mime_type: str) -> str:
    """Extract plain text from raw bytes according to MIME type."""
    mt = mime_type.split(";")[0].strip()

    if mt in ("text/plain", "text/markdown", "text/csv", "application/json"):
        return data.decode("utf-8", errors="replace")

    if mt == "text/html":
        text = data.decode("utf-8", errors="replace")
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r" {3,}", "  ", text).strip()

    if mt == "application/pdf":
        return _pdf_to_text(data)

    if mt in (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    ):
        return _excel_to_text(data)

    # Best-effort fallback
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        logger.warning("Cannot decode document as text", extra={"mime_type": mime_type})
        return ""


def _excel_to_text(data: bytes) -> str:
    import io

    try:
        import openpyxl

        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        parts: list[str] = []
        for sheet in wb.worksheets:
            parts.append(sheet.title)
            for row in sheet.iter_rows(values_only=True):
                cells = [str(c) if c is not None else "" for c in row]
                if any(cells):
                    parts.append("\t".join(cells))
        return "\n".join(parts)
    except ImportError:
        logger.warning("openpyxl not installed — cannot extract Excel text")
        return ""
    except Exception:
        logger.exception("Excel extraction failed")
        return ""


def _pdf_to_text(data: bytes) -> str:
    import io

    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    except ImportError:
        logger.warning("pypdf not installed — cannot extract PDF text")
        return ""
    except Exception:
        logger.exception("PDF extraction failed")
        return ""


# Numbered headings: 1–2 digit section numbers only ("1 Foo", "1.2.3 Foo").
# Requires the word after the number to start with an uppercase letter followed by a
# lowercase letter — this eliminates module codes ("MMG04"), years ("1727"), and
# large page numbers ("34 MMG04") which are all-caps or exceed 2 digits.
_NUMBERED_HEADING_RE = re.compile(r"^(?:[1-9]\d?)(?:\.\d+)*\.?\s+[A-ZÄÖÜ][a-zäöüß]\w*")

# Standalone keyword headings (case-insensitive).
# "Aufgabe" and "Lernziel" removed — they fire on exercise questions, not sections.
_KEYWORD_HEADING_RE = re.compile(
    r"^(?:Kapitel|Abschnitt|Einleitung|Zusammenfassung|Anhang)\b",
    re.IGNORECASE,
)


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 120:
        return False
    # Headings don't end with sentence-final punctuation
    if stripped.endswith((".", "!", "?", ",", ";")):
        return False
    return bool(_NUMBERED_HEADING_RE.match(stripped) or _KEYWORD_HEADING_RE.match(stripped))


def _detect_chapter(line: str) -> str:
    """Return a normalised chapter label from a heading line."""
    return line.strip()


def split_text(
    text: str,
    chunk_size: int = 1500,
    overlap: int = 200,
) -> list[str]:
    """Split text into overlapping chunks (plain strings, no metadata)."""
    return [str(c["content"]) for c in split_text_with_metadata(text, chunk_size, overlap)]


def split_text_with_metadata(
    text: str,
    chunk_size: int = 1500,
    overlap: int = 200,
) -> list[dict[str, object]]:
    """Split text into chunks, annotating each with the nearest chapter heading."""
    if not text.strip():
        return []

    lines = text.splitlines()
    paragraphs: list[tuple[str, str]] = []  # (paragraph_text, chapter_at_that_point)
    current_chapter = ""
    current_para_lines: list[str] = []

    def _flush() -> None:
        para = "\n".join(current_para_lines).strip()
        if para:
            paragraphs.append((para, current_chapter))
        current_para_lines.clear()

    for line in lines:
        if _is_heading(line):
            _flush()
            current_chapter = _detect_chapter(line)
            current_para_lines.append(line)
        elif line.strip() == "":
            _flush()
        else:
            current_para_lines.append(line)
    _flush()

    if not paragraphs:
        return []

    # Merge paragraphs into chunks respecting chunk_size
    chunks: list[tuple[str, str]] = []  # (text, chapter)
    current_text = ""
    current_ch = ""

    for para_text, chapter in paragraphs:
        if not current_text:
            current_text, current_ch = para_text, chapter
        elif len(current_text) + 2 + len(para_text) <= chunk_size:
            current_text = f"{current_text}\n\n{para_text}"
            # Update chapter only if a new heading started this paragraph
            if chapter:
                current_ch = chapter
        else:
            chunks.append((current_text, current_ch))
            tail = current_text[-overlap:].strip() if len(current_text) > overlap else current_text
            current_text = f"{tail}\n\n{para_text}".strip() if tail else para_text
            current_ch = chapter or current_ch

    if current_text:
        chunks.append((current_text, current_ch))

    # Second pass: break oversized chunks at sentence boundaries
    result: list[dict[str, object]] = []
    for chunk_text, chapter in chunks:
        if len(chunk_text) <= chunk_size * 2:
            result.append({"content": chunk_text, "chapter": chapter})
        else:
            for sub in _split_sentences(chunk_text, chunk_size, overlap):
                result.append({"content": sub, "chapter": chapter})
    return result


def _split_sentences(text: str, chunk_size: int, overlap: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""
    for sent in sentences:
        if not current:
            current = sent
        elif len(current) + 1 + len(sent) <= chunk_size:
            current = f"{current} {sent}"
        else:
            chunks.append(current)
            tail = current[-overlap:].strip() if len(current) > overlap else current
            current = f"{tail} {sent}".strip() if tail else sent
    if current:
        chunks.append(current)
    return chunks
