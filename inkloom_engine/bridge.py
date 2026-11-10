"""Entry point for the team repo's backend (engine/adapter.py).

review_for_api(text) returns the shape engine/formatter.py and the SQLite layer already use:
  findings[]: issue_type, severity, excerpt, explanation, cited_source, suggested_fix, uncertainty
plus extras the UI can use: start, end (offsets into `text`), advice.
Anything that could contain personal data is masked, so values are never echoed back.
"""
from __future__ import annotations

from typing import Optional

from .llm import llm_from_env
from .models import Citation, IssueType, Uncertainty
from .pack import load_kb
from .pipeline import review
from .text import redact_pii

ISSUE_NAME = {
    IssueType.CLAIMS_COMPLIANCE: "unsupported_claim",
    IssueType.FACT_MISMATCH: "stale_fact",
    IssueType.TERMINOLOGY: "terminology",
    IssueType.PII: "pii",
    IssueType.ACCESSIBILITY: "accessibility",
    IssueType.TONE_OF_VOICE: "tone",
    IssueType.INCLUSIVE_LANGUAGE: "inclusive_language",
    IssueType.LEGAL_DISCLOSURE: "legal_disclosure",
    IssueType.FORMATTING: "formatting",
}
UNCERTAINTY = {
    Uncertainty.RULE_BASED: "Source found / rule-based",
    Uncertainty.SOURCE_FOUND: "Source found (AI finding, citation verified)",
    Uncertainty.MODEL_UNCERTAIN: "AI uncertain: needs human check",
    Uncertainty.NO_SOURCE_FOUND: "No source found",
}


def _source(c: Optional[Citation]) -> str:
    if c is None:
        return "No source found"
    if c.kind == "fact":
        return f"{c.name} (approved fact {c.section}, v{c.version}, {c.effective_date}): {c.excerpt}"
    return f"{c.name}, {c.section} (v{c.version}, {c.effective_date})"


def review_for_api(text: str, pack_path=None, llm="env") -> dict:
    """llm="env" uses the model only if ANTHROPIC_API_KEY is set; pass None to force rules-only."""
    client = llm_from_env() if llm == "env" else llm
    result = review(text, load_kb(pack_path), client)
    findings = [{
        "issue_type": ISSUE_NAME[f.issue_type],
        "severity": f.severity.value.lower(),
        "excerpt": redact_pii(f.flagged_text),
        "explanation": redact_pii(f.explanation),
        "cited_source": _source(f.citation),
        "suggested_fix": redact_pii(f.suggested_fix or f.advice or ""),
        "uncertainty": UNCERTAINTY[f.uncertainty],
        "start": f.start, "end": f.end,
        "advice": redact_pii(f.advice or ""),
    } for f in result.findings]
    return {"findings": findings, "engine": "inkloom_engine" + ("+llm" if client else ""),
            "warnings": result.warnings, "disclosure": result.disclosure,
            "knowledge_versions": result.knowledge_versions}
