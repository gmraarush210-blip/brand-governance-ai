"""Adapter to the contract Varun's frontend expects (see src/lib/types.ts `Finding`).

The frontend highlights one span per finding and rebuilds revised text by replacing
[start, end), so spans MUST NOT overlap. This adapter therefore returns one finding per
sentence: the most severe issue is primary, other issues in that sentence are listed in its
explanation, and the suggested fix combines every deterministic correction for the sentence.

Optional stdlib HTTP server (demo / integration testing):
    python -m inkloom_engine.frontend_api            # serves POST /api/review/analyze on :8000
"""
from __future__ import annotations

import base64
import binascii
import json
import os
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

from .checks import apply_edits
from .knowledge import KnowledgeBase
from .llm import LLMClient, llm_from_env
from .models import Finding, IssueType, ReviewResult
from .pipeline import review
from .text import ExtractionError, extract_pdf_text

CATEGORY = {  # engine issue type -> categories the frontend already knows
    IssueType.CLAIMS_COMPLIANCE: "Claims & Compliance",
    IssueType.FACT_MISMATCH: "Claims & Compliance",
    IssueType.TONE_OF_VOICE: "Tone of Voice",
    IssueType.TERMINOLOGY: "Terminology",
    IssueType.INCLUSIVE_LANGUAGE: "Inclusive Language",
    IssueType.LEGAL_DISCLOSURE: "Legal & Disclosure",
    IssueType.FORMATTING: "Formatting",
    IssueType.ACCESSIBILITY: "Formatting",
    IssueType.PII: "Legal & Disclosure",
}
LABEL = {t: t.value.replace("_", " ").capitalize() for t in IssueType}


def _primary(group: list[Finding]) -> Finding:
    return max(group, key=lambda f: (f.severity.rank, f.citation is not None))


def to_frontend(result: ReviewResult, id_prefix: str = "f") -> list[dict]:
    by_sentence: dict[tuple[int, int], list[Finding]] = defaultdict(list)
    for f in result.findings:
        by_sentence[(f.start, f.end)].append(f)
    out: list[dict] = []
    for n, ((start, end), group) in enumerate(sorted(by_sentence.items())):
        p = _primary(group)
        others = [g for g in group if g is not p]
        explanation = p.explanation
        if others:
            explanation += " Also in this sentence: " + " ".join(
                f"{LABEL[g.issue_type]}: {g.explanation}" for g in others)
        edits = tuple(e for g in group for e in g.edits)
        suggestion = apply_edits(p.flagged_text, edits) if edits else p.suggested_fix
        if suggestion == p.flagged_text:
            suggestion = None
        c = p.citation
        out.append({
            "id": f"{id_prefix}_{n}",
            "sentence": p.flagged_text, "start": start, "end": end,
            "category": CATEGORY[p.issue_type],
            "severity": p.severity.value.lower(),
            "explanation": explanation,
            "source": None if c is None else {
                "guidelineName": c.name, "section": c.section, "version": c.version,
                "date": c.effective_date, "excerpt": c.excerpt},
            "suggestion": suggestion,
            "decision": "open",
            "uncertainty": p.uncertainty.value,
            "issueTypes": sorted({g.issue_type.value for g in group}),
            "advice": p.advice,
        })
    return out


def analyze(payload: dict, kb: KnowledgeBase, llm: Optional[LLMClient] = None) -> dict:
    """Body of POST /api/review/analyze.
    Request : {"text": str} or {"pdf_base64": str}
    Response: {"findings": [...], "mode", "warnings", "disclosure", "knowledgeVersions", "extractedText"?}
    """
    text = payload.get("text")
    extracted = None
    if not text and payload.get("pdf_base64"):
        try:
            ex = extract_pdf_text(base64.b64decode(payload["pdf_base64"], validate=True))
        except binascii.Error as exc:
            raise ExtractionError("The uploaded file could not be decoded.") from exc
        text, extracted = ex.text, ex
    if not isinstance(text, str) or not text.strip():
        raise ExtractionError("Please provide text or a PDF to review.")
    result = review(text, kb, llm)
    body = {
        "findings": to_frontend(result), "mode": result.mode,
        "warnings": result.warnings + (extracted.warnings if extracted else []),
        "disclosure": result.disclosure, "knowledgeVersions": result.knowledge_versions,
    }
    if extracted:
        body["extractedText"] = text
    return body


def make_handler(kb: KnowledgeBase, llm: Optional[LLMClient]):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: dict) -> None:
            data = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", os.getenv("INKLOOM_CORS_ORIGIN", "http://localhost:5173"))
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(data)

        def do_OPTIONS(self):  # CORS preflight
            self._send(204, {})

        def do_POST(self):
            if self.path != "/api/review/analyze":
                return self._send(404, {"error": "Not found"})
            try:
                length = int(self.headers.get("Content-Length", 0))
                if length > 15 * 1024 * 1024:
                    return self._send(413, {"error": "Request too large."})
                payload = json.loads(self.rfile.read(length) or b"{}")
                self._send(200, analyze(payload, kb, llm))
            except (ExtractionError, json.JSONDecodeError, ValueError) as exc:
                self._send(400, {"error": str(exc)})
            except Exception:  # never leak internals to the client
                self._send(500, {"error": "The review engine hit an unexpected error."})

        def log_message(self, *args):  # keep submitted content out of server logs
            pass
    return Handler


if __name__ == "__main__":
    from .pack import load_kb
    kb = load_kb(os.getenv("INKLOOM_KB", str(Path(__file__).resolve().parent.parent / "data" / "seed_knowledge.json")))
    llm = llm_from_env()
    print(f"Inkloom review engine on :8000 (mode: {'rules+llm' if llm else 'rules only'})")
    ThreadingHTTPServer(("127.0.0.1", 8000), make_handler(kb, llm)).serve_forever()
