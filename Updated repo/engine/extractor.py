"""
Text and PDF extraction. Owner: M Tejas Navada
Limits: 10 MB, 50 pages, no password-protected files, no scanned (image-only) PDFs (no OCR in the MVP).
"""
import io

MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 50


class ExtractionError(Exception):
    pass


def normalize(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\x00", "").strip()


def extract_pdf_text(data: bytes) -> str:
    if not data:
        raise ExtractionError("empty file")
    if len(data) > MAX_BYTES:
        raise ExtractionError("PDF is larger than 10 MB")
    if not data.lstrip().startswith(b"%PDF"):
        raise ExtractionError("not a valid PDF")
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ExtractionError("PDF is password-protected")
        if len(reader.pages) > MAX_PAGES:
            raise ExtractionError(f"PDF has more than {MAX_PAGES} pages")
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except ExtractionError:
        raise
    except Exception as e:
        raise ExtractionError(f"unreadable PDF ({type(e).__name__})") from e
    text = normalize(text)
    if not text:
        raise ExtractionError("no extractable text (scanned or empty PDF)")
    return text
