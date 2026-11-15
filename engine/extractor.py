"""
Text and PDF extraction. Owner: M Tejas Navada
"""
import io


class ExtractionError(Exception):
    pass


def normalize(text: str) -> str:
    return text.replace("\r\n", "\n").strip()


def extract_pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as e:
        raise ExtractionError(f"unreadable PDF ({type(e).__name__})") from e
    text = normalize(text)
    if not text:
        raise ExtractionError("no extractable text (scanned or empty PDF)")
    return text
