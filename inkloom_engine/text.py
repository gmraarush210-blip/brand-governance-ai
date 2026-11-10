"""Text utilities: PDF extraction, sentence splitting with offsets, PII masking, readability."""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 50


class ExtractionError(ValueError):
    """Raised with a user-presentable message when a document cannot be read."""


@dataclass
class Extraction:
    text: str
    pages: int
    warnings: list[str] = field(default_factory=list)


def extract_pdf_text(data: bytes) -> Extraction:
    """Extract selectable text from a PDF. Scanned/image-only PDFs are not OCR'd (MVP)."""
    if not data:
        raise ExtractionError("This file appears to be empty.")
    if len(data) > MAX_PDF_BYTES:
        raise ExtractionError("This PDF is larger than 10 MB.")
    if not data.lstrip().startswith(b"%PDF"):
        raise ExtractionError("This file is not a valid PDF.")

    warnings: list[str] = []
    pages_text: list[str] = []
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ExtractionError("This PDF is password-protected. Remove the password and retry.")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise ExtractionError(f"This PDF has more than {MAX_PDF_PAGES} pages.")
        pages_text = [(p.extract_text() or "") for p in reader.pages]
    except ExtractionError:
        raise
    except ImportError:
        try:
            import pdfplumber

            with pdfplumber.open(io.BytesIO(data)) as pdf:
                if len(pdf.pages) > MAX_PDF_PAGES:
                    raise ExtractionError(f"This PDF has more than {MAX_PDF_PAGES} pages.")
                pages_text = [(p.extract_text() or "") for p in pdf.pages]
        except ImportError as exc:  # pragma: no cover
            raise ExtractionError("No PDF library is installed (pypdf or pdfplumber).") from exc
    except Exception as exc:
        raise ExtractionError("This PDF could not be read. It may be corrupted.") from exc

    text = "\n\n".join(t.strip() for t in pages_text if t.strip())
    text = text.replace("\x00", "")
    if len(text.strip()) < 20:
        raise ExtractionError(
            "No selectable text was found. Scanned or image-only PDFs are not supported in this MVP."
        )
    if any(not t.strip() for t in pages_text):
        warnings.append("Some pages contained no selectable text (images or scans) and were not reviewed.")
    return Extraction(text=text, pages=len(pages_text), warnings=warnings)


_CLOSERS = "\"')]”’"


def split_sentences(text: str) -> list[tuple[str, int, int]]:
    """Return (sentence, start, end) with offsets into `text`.

    Splits on . ! ? followed by whitespace/end, and on newlines. Decimals ("3.5x"),
    URLs and abbreviations inside a word are kept intact.
    """
    out: list[tuple[str, int, int]] = []
    n, i, seg_start = len(text), 0, 0

    def flush(end: int) -> None:
        seg = text[seg_start:end]
        stripped = seg.strip()
        if stripped:
            start = seg_start + (len(seg) - len(seg.lstrip()))
            out.append((stripped, start, start + len(stripped)))

    while i < n:
        c = text[i]
        if c == "\n":
            flush(i)
            seg_start = i + 1
            i += 1
        elif c in ".!?":
            j = i
            while j < n and text[j] in ".!?":
                j += 1
            while j < n and text[j] in _CLOSERS:
                j += 1
            if j >= n or text[j].isspace():
                flush(j)
                seg_start = j
            i = j
        else:
            i += 1
    flush(n)
    return out


_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# Phones are matched by shape (not "any long digit run") so dates, prices and ids are left alone:
_PHONE = re.compile(
    r"(?<![\w.+-])(?:"
    r"(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}"                   # Indian mobile, 10 digits
    r"|\+\d{1,3}[\s-]?\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}"      # international, must start with +
    r"|\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}"                      # 3-3-4 formatted
    r")(?![\w-])"
)
_ID = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b|\b\d{4}\s\d{4}\s\d{4}\b")  # PAN-style, 12-digit grouped ids
PII_KINDS = (("email address", _EMAIL, "[EMAIL]"), ("phone number", _PHONE, "[PHONE]"),
             ("ID number", _ID, "[ID]"))
PLACEHOLDERS = ("[EMAIL]", "[ID]", "[PHONE]")


def find_pii(text: str) -> list[str]:
    """Labels of the kinds of personal data present in `text` (values are never returned)."""
    return [label for label, rx, _ in PII_KINDS if rx.search(text)]


def redact_pii(text: str) -> str:
    """Mask obvious personal data before text leaves the machine or is shown in a log/finding."""
    for _, rx, token in PII_KINDS:
        text = rx.sub(token, text)
    return text


def count_syllables(word: str) -> int:
    word = re.sub(r"[^a-z]", "", word.lower())
    if not word:
        return 0
    groups = re.findall(r"[aeiouy]+", word)
    n = len(groups)
    if word.endswith("e") and not word.endswith(("le", "ee")) and n > 1:
        n -= 1
    return max(n, 1)


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z'’-]*", text)


def flesch_kincaid_grade(text: str) -> float:
    sents = split_sentences(text)
    ws = words(text)
    if not sents or not ws:
        return 0.0
    syll = sum(count_syllables(w) for w in ws)
    return 0.39 * (len(ws) / len(sents)) + 11.8 * (syll / len(ws)) - 15.59
