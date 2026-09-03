"""Text extraction for PDF and DOCX with an OCR fallback.

Scanned Vietnamese gazette PDFs are common in this corpus: roughly one in ten
official attachments has no usable text layer.  ``extract_pdf`` therefore checks
each page and falls back to Tesseract (``vie`` traineddata) only for the pages
that need it, so a 60-page circular with two scanned annexes costs two OCR
passes instead of sixty.

Every optional dependency is imported lazily.  A machine without PyMuPDF or
Tesseract still ingests the digital-text majority of the corpus and reports the
skipped pages instead of crashing.
"""

from __future__ import annotations

import logging
from pathlib import Path

from virag.schemas import DocumentMeta, ExtractedDocument, PageText
from virag.settings import Settings, get_settings

logger = logging.getLogger(__name__)

_OCR_UNAVAILABLE_LOGGED = False


class ExtractionError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------


def _pdf_text_layer(path: Path) -> list[str]:
    """Return per-page text from the PDF text layer (empty strings when absent)."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise ExtractionError("pypdf is required to read PDF files") from exc

    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        raise ExtractionError(f"cannot open PDF {path.name}: {exc}") from exc

    pages: list[str] = []
    for index, page in enumerate(reader.pages):
        try:
            pages.append(page.extract_text() or "")
        except Exception as exc:
            logger.warning("text extraction failed on %s page %d: %s", path.name, index + 1, exc)
            pages.append("")
    return pages


def _ocr_available() -> bool:
    global _OCR_UNAVAILABLE_LOGGED
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        if not _OCR_UNAVAILABLE_LOGGED:
            logger.warning("pytesseract not installed - OCR fallback disabled")
            _OCR_UNAVAILABLE_LOGGED = True
        return False
    try:
        import fitz  # noqa: F401  (PyMuPDF, used to rasterise without poppler)
    except ImportError:
        try:
            import pdf2image  # noqa: F401
        except ImportError:
            if not _OCR_UNAVAILABLE_LOGGED:
                logger.warning("neither PyMuPDF nor pdf2image installed - OCR fallback disabled")
                _OCR_UNAVAILABLE_LOGGED = True
            return False
    return True


def _render_page(path: Path, page_number: int, dpi: int):
    """Rasterise a single 1-indexed PDF page to a PIL image."""
    try:
        import fitz

        with fitz.open(str(path)) as doc:
            page = doc.load_page(page_number - 1)
            zoom = dpi / 72.0
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            from io import BytesIO

            from PIL import Image

            return Image.open(BytesIO(pix.tobytes("png")))
    except ImportError:
        pass

    from pdf2image import convert_from_path

    images = convert_from_path(str(path), dpi=dpi, first_page=page_number, last_page=page_number)
    if not images:
        raise ExtractionError(f"pdf2image returned no image for page {page_number}")
    return images[0]


def _ocr_page(path: Path, page_number: int, settings: Settings) -> str:
    import pytesseract

    image = _render_page(path, page_number, settings.ocr_dpi)
    # --psm 4: assume a single column of variable-size text, which matches the
    # single-column layout of Vietnamese gazette scans better than the default.
    return pytesseract.image_to_string(image, lang=settings.ocr_language, config="--psm 4")


def extract_pdf(path: Path, meta: DocumentMeta, settings: Settings | None = None) -> ExtractedDocument:
    settings = settings or get_settings()
    raw_pages = _pdf_text_layer(path)

    ocr_wanted = [
        index
        for index, text in enumerate(raw_pages)
        if len(text.strip()) < settings.ocr_min_chars_per_page
    ]
    use_ocr = bool(ocr_wanted) and settings.ocr_enabled and _ocr_available()

    pages: list[PageText] = []
    ocr_count = 0
    for index, text in enumerate(raw_pages):
        page_number = index + 1
        method: str = "text"
        if index in ocr_wanted and use_ocr:
            try:
                ocr_text = _ocr_page(path, page_number, settings)
                if len(ocr_text.strip()) > len(text.strip()):
                    text = ocr_text
                    method = "ocr"
                    ocr_count += 1
            except Exception as exc:
                logger.warning("OCR failed on %s page %d: %s", path.name, page_number, exc)
        pages.append(PageText(page_number=page_number, text=text, extraction_method=method))

    return ExtractedDocument(
        meta=meta,
        pages=pages,
        ocr_page_count=ocr_count,
        source_path=str(path),
    )


# ---------------------------------------------------------------------------
# DOCX
# ---------------------------------------------------------------------------


def extract_docx(path: Path, meta: DocumentMeta) -> ExtractedDocument:
    try:
        import docx
    except ImportError as exc:
        raise ExtractionError("python-docx is required to read DOCX files") from exc

    document = docx.Document(str(path))
    parts: list[str] = [p.text for p in document.paragraphs if p.text.strip()]
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            if any(cells):
                # Pipe separators keep rate tables readable once chunked.
                parts.append(" | ".join(cells))

    text = "\n".join(parts)
    return ExtractedDocument(
        meta=meta,
        pages=[PageText(page_number=1, text=text, extraction_method="docx")],
        source_path=str(path),
    )


# ---------------------------------------------------------------------------
# HTML (crawler side-car text files)
# ---------------------------------------------------------------------------


def extract_text_file(path: Path, meta: DocumentMeta) -> ExtractedDocument:
    text = path.read_text(encoding="utf-8", errors="replace")
    return ExtractedDocument(
        meta=meta,
        pages=[PageText(page_number=1, text=text, extraction_method="html")],
        source_path=str(path),
    )


def extract_document(path: Path, meta: DocumentMeta, settings: Settings | None = None) -> ExtractedDocument:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf(path, meta, settings)
    if suffix in {".docx", ".doc"}:
        return extract_docx(path, meta)
    if suffix in {".txt", ".html", ".htm"}:
        return extract_text_file(path, meta)
    raise ExtractionError(f"unsupported file type: {path.suffix}")
