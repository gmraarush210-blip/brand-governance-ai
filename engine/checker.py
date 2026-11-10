"""
Rule-based checks with cited retrieval.
Terminology, unsupported claims, stale facts, PII, accessibility.
Owner: M Tejas Navada

Rules run first; missing evidence is labelled "No source found", never silently passed.
"""
import json
import re
from pathlib import Path

from .formatter import format_result, to_finding

PACK_PATH = Path(__file__).resolve().parent.parent / "data" / "fictional_brand_pack.json"
RULE_SET = ["terminology", "unsupported_claim", "stale_fact", "brand_name", "pii", "accessibility"]

ABSOLUTE_CLAIMS = [
    r"fastest in the world", r"\bzero (?:errors|defects|risk|bugs)\b", r"\b100\s?%",
    r"\bbest in (?:the )?(?:world|class)\b", r"\bnumber one\b",
]
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# Matched by shape (Indian mobile, +international, 3-3-4) so dates, prices and long numbers are not flagged.
PHONE = re.compile(
    r"(?<![\w.+-])(?:(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}"
    r"|\+\d{1,3}[\s-]?\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}"
    r"|\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4})(?![\w-])")


def load_pack(path: Path = PACK_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _source(pack: dict, gid: str) -> str:
    for g in pack.get("guidelines", []):
        if g["id"] == gid:
            return f'{pack["brand"]} Brand Pack, {g["section"]} (v{pack["version"]}, {pack["date"]})'
    return "No source found"


def _sentence(text: str, start: int, end: int) -> str:
    s = max(text.rfind(".", 0, start), text.rfind("\n", 0, start)) + 1
    e_candidates = [i for i in (text.find(".", end), text.find("\n", end)) if i != -1]
    e = min(e_candidates) + 1 if e_candidates else len(text)
    return text[s:e].strip()


def _mask(s: str) -> str:
    return PHONE.sub("[PHONE]", EMAIL.sub("[EMAIL]", s))


def check(text: str, pack: dict | None = None) -> dict:
    pack = pack or load_pack()
    out: list[dict] = []

    # 1. Terminology (2.2)
    preferred = pack["terminology"]["preferred"]
    for term in pack["terminology"]["avoid"]:
        for m in re.finditer(rf"\b{re.escape(term)}\b", text, re.I):
            repl = preferred.get(term.lower(), "a softer phrasing")
            out.append(to_finding(
                "terminology", "high", _sentence(text, m.start(), m.end()),
                f'"{m.group(0)}" is a prohibited term: it implies a guaranteed or curative outcome.',
                _source(pack, "2.2"), f'Replace with "{repl}".'))

    # 2. Unsupported absolute claims (2.1)
    for pat in ABSOLUTE_CLAIMS:
        for m in re.finditer(pat, text, re.I):
            out.append(to_finding(
                "unsupported_claim", "high", _sentence(text, m.start(), m.end()),
                "Absolute performance claim. The approved fact sheet has no verified entry for it.",
                _source(pack, "2.1"),
                'Soften, e.g. "built for speed" or "designed to help reduce errors", or add a verified fact.',
                "Source found / rule-based. Routed to an authorised reviewer (High)."))

    # 3. Stale / conflicting facts
    for fact in pack.get("facts", []):
        if fact["claim"] == "founded":
            for m in re.finditer(r"founded (?:in )?(\d{4})", text, re.I):
                if m.group(1) != fact["value"]:
                    out.append(to_finding(
                        "stale_fact", "high", _sentence(text, m.start(), m.end()),
                        f'Draft says founded {m.group(1)}; the approved fact sheet says {fact["value"]}.',
                        f'{pack["brand"]} Brand Pack, approved facts: founded = {fact["value"]} (v{pack["version"]})',
                        f"Use {fact['value']}.", "Source found / rule-based."))

    # 4. Brand name capitalisation (3.1)
    for m in re.finditer(r"(?<![@\w.])(ACME|acme)(?![\w.@])", text):
        out.append(to_finding(
            "terminology", "low", _sentence(text, m.start(), m.end()),
            f'Brand name written as "{m.group(1)}".', _source(pack, "3.1"), 'Write "Acme".'))

    # 5. PII (4.1) — values are masked, never echoed
    for label, rx in (("email address", EMAIL), ("phone number", PHONE)):
        for m in rx.finditer(text):
            out.append(to_finding(
                "pii", "high", _mask(_sentence(text, m.start(), m.end())),
                f"A personal {label} appears in publishable copy (value masked here).",
                _source(pack, "4.1"), "Remove it and link to the official contact page."))

    # 6. Accessibility (5.1)
    if re.search(r"!\[\]\(", text) or re.search(r"<img(?![^>]*\balt=)[^>]*>", text, re.I):
        out.append(to_finding("accessibility", "medium", "", "An image has no alt text.",
                              _source(pack, "5.1"), "Add a short descriptive alt text."))
    sentences = [s for s in re.split(r"[.!?]+\s", text) if s.strip()]
    if sentences:
        avg = sum(len(s.split()) for s in sentences) / len(sentences)
        if avg > 25:
            out.append(to_finding(
                "accessibility", "low", "", f"Average sentence length is {avg:.0f} words (limit 25).",
                _source(pack, "5.1"), "Split long sentences.", "Heuristic / rule-based."))

    return format_result({"findings": out}, engine="builtin")
