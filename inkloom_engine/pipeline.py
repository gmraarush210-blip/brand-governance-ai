"""Top-level entry point: review(text, kb, llm) -> ReviewResult."""
from __future__ import annotations

from typing import Optional

from .checks import reading_level_warning, run_accessibility, run_fact_checks, run_pii, run_rules
from .knowledge import KnowledgeBase
from .llm import LLMClient, run_llm_review
from .models import Finding, ReviewResult
from .text import split_sentences

DISCLOSURE = (
    "Findings are suggestions produced by automated rules, retrieval over your approved guidelines and facts"
    "{llm}. Nothing is changed, approved or published automatically; a human reviewer makes the final decision."
)
LLM_DISCLOSURE = (
    ", and an AI language model. Sentences from the submission (with emails, phone numbers and ID numbers masked) "
    "and the relevant guideline excerpts are sent to the model provider to generate findings"
)


def review(text: str, kb: KnowledgeBase, llm: Optional[LLMClient] = None) -> ReviewResult:
    """Review `text` without modifying it. Offsets in findings index into `text` as given."""
    warnings: list[str] = []
    sentences = split_sentences(text)
    if not sentences:
        return ReviewResult([], "rules", ["There is no text to review."], kb.version_labels(), DISCLOSURE.format(llm=""))

    found: list[Finding] = []
    found += run_rules(sentences, kb)
    found += run_fact_checks(sentences, kb, warnings)
    found += run_accessibility(text, sentences, kb)
    found += run_pii(sentences, kb)
    if (w := reading_level_warning(text)):
        warnings.append(w)

    mode = "rules"
    if llm is not None:
        mode = "rules+llm"
        found += run_llm_review(sentences, kb, llm, warnings)

    return ReviewResult(_dedupe(found), mode, warnings, kb.version_labels(),
                        DISCLOSURE.format(llm=LLM_DISCLOSURE if llm is not None else ""))


def _dedupe(findings: list[Finding]) -> list[Finding]:
    """Keep every distinct deterministic check; drop a model finding if a rule/fact/accessibility check
    already reported the same issue type on that sentence; collapse repeated model findings."""
    det = [f for f in findings if f.origin != "llm"]
    seen = {(f.start, f.end, f.issue_type) for f in det}
    kept = {(f.start, f.end, f.issue_type, f.rule_id): f for f in det}
    for f in sorted((f for f in findings if f.origin == "llm"), key=lambda f: (f.citation is None, -f.severity.rank)):
        if (f.start, f.end, f.issue_type) not in seen:
            kept.setdefault((f.start, f.end, f.issue_type, "llm"), f)
    return sorted(kept.values(), key=lambda f: (f.start, -f.severity.rank, f.issue_type.value, f.rule_id))
