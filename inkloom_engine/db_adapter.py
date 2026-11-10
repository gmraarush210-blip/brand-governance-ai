"""Glue between the engine and Aarush's SQLAlchemy layer (Database_Fixed.py / Brand_Governance_Schema_Fixed.py).

Imports are done inside functions so the engine itself has no SQLAlchemy dependency.
Put the backend files on PYTHONPATH (or next to this package) to use these helpers.
"""
from __future__ import annotations

from typing import Optional

from .knowledge import KnowledgeBase, split_sections
from .models import Chunk, Fact, ReviewResult


def load_knowledge(session) -> KnowledgeBase:
    """Build a KnowledgeBase from the latest version of every active guideline and approved fact."""
    from sqlalchemy import select
    from Brand_Governance_Schema_Fixed import ApprovedFact, BrandGuideline

    chunks: list[Chunk] = []
    for g in session.scalars(select(BrandGuideline).where(BrandGuideline.is_active.is_(True))):
        if not g.versions:
            continue
        v = g.versions[-1]  # ordered by version_number
        for sid, body in split_sections(v.content):
            chunks.append(Chunk(g.code, g.title, str(v.version_number), v.effective_date.date().isoformat(),
                                sid, body, g.id, v.id))
    facts: list[Fact] = []
    for f in session.scalars(select(ApprovedFact).where(ApprovedFact.is_active.is_(True))):
        if not f.versions:
            continue
        v = f.versions[-1]
        facts.append(Fact(f.fact_key, f.title, v.approved_value, str(v.version_number),
                          v.effective_date.date().isoformat(), v.source_reference or "", f.description or "",
                          v.expires_at.date().isoformat() if v.expires_at else None, f.id, v.id))
    return KnowledgeBase(chunks, facts)


def persist_findings(session, submission, result: ReviewResult) -> list:
    """Save engine findings via Database_Fixed.add_ai_finding. Caller commits.

    Offsets index into the text that was reviewed, which must be submission.raw_content
    (add_ai_finding verifies raw_content[start:end] == flagged_text)."""
    from Brand_Governance_Schema_Fixed import (ApprovedFactVersion, BrandGuideline, FindingSeverity,
                                              FindingUncertainty, GuidelineVersion)
    from Database_Fixed import add_ai_finding

    saved = []
    for f in result.findings:
        c = f.citation
        guideline = version = fact_version = None
        if c and c.kind == "guideline":
            guideline = session.get(BrandGuideline, c.guideline_id) if c.guideline_id else None
            version = session.get(GuidelineVersion, c.version_id) if c.version_id else None
        elif c and c.kind == "fact" and c.version_id:
            fact_version = session.get(ApprovedFactVersion, c.version_id)
        saved.append(add_ai_finding(
            session, submission=submission, issue_type=f.issue_type.value,
            start_char=f.start, end_char=f.end,
            flagged_text=f.flagged_text, explanation=f.explanation,
            severity=FindingSeverity(f.severity.value), uncertainty=FindingUncertainty(f.uncertainty.value),
            suggested_fix=f.suggested_fix, cited_guideline=guideline, cited_guideline_version=version,
            cited_fact_version=fact_version, source_reference=c.reference if c else None))
    return saved


def review_submission(session, submission, llm=None) -> ReviewResult:
    """Load knowledge, review the submission's current content, store findings."""
    from .pipeline import review

    result = review(submission.raw_content, load_knowledge(session), llm)
    persist_findings(session, submission, result)
    return result
