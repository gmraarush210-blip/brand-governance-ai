"""Deterministic checks: guideline rules, approved-fact comparison, accessibility.

Every rule names the guideline section it enforces. The citation is only attached if that
section really exists in the loaded knowledge base; otherwise the finding is still reported
but marked NO_SOURCE_FOUND (we never invent a source).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Callable, Optional

from .knowledge import KnowledgeBase, tokenize
from .models import Chunk, Citation, Fact, Finding, IssueType, Severity, Uncertainty
from .text import find_pii, flesch_kincaid_grade, words

MAX_GRADE = 9.0
MAX_SENTENCE_WORDS = 30


def citation_from_chunk(c: Chunk) -> Citation:
    return Citation("guideline", c.guideline_title, c.section, c.version, c.effective_date,
                    c.text, c.guideline_id, c.version_id)


def citation_from_fact(f: Fact) -> Citation:
    return Citation("fact", f.title, f.key, f.version, f.effective_date,
                    f"{f.title}: {f.value}" + (f" (source: {f.source_reference})" if f.source_reference else ""),
                    None, f.version_id)


@dataclass(frozen=True)
class Rule:
    id: str
    pattern: re.Pattern
    issue_type: IssueType
    severity: Severity
    explanation: str
    guideline: Optional[tuple[str, str]]          # (guideline_code, section label)
    replace: Optional[Callable[[re.Match], Optional[str]]] = None  # None result -> no automatic edit
    advice: Optional[str] = None


def _sub(mapping: dict[str, str], default: str = "") -> Callable[[re.Match], str]:
    def fn(m: re.Match) -> str:
        w = m.group(0)
        new = mapping.get(w.lower(), default)
        return new.capitalize() if new and w[0].isupper() else new
    return fn


RULES: list[Rule] = [
    Rule("absolute_guarantee", re.compile(r"\bguarantee(?:d|s)?\b|\b100\s?%\s*(?:safe|secure|accurate|effective)\b", re.I),
         IssueType.CLAIMS_COMPLIANCE, Severity.CRITICAL,
         "Absolute guarantees create legal exposure unless backed by a documented warranty.",
         ("MARKETING_CLAIMS", "§2.1"),
         _sub({"guarantee": "aim", "guaranteed": "designed", "guarantees": "aims"}, "designed")),
    Rule("superlative", re.compile(r"\bbest in the (?:world|market|industry)\b|\bnumber one\b|#1\b|\b(?:the )?best\b(?! practice)", re.I),
         IssueType.CLAIMS_COMPLIANCE, Severity.HIGH,
         "Superlative or absolute claims need a dated, independent source.",
         ("MARKETING_CLAIMS", "§2.3"),
         lambda m: "highly rated" if "best" in m.group(0).lower() else "a leading"),
    Rule("health_risk_claim", re.compile(r"\b(?:cures?|clinically proven|risk[- ]free)\b", re.I),
         IssueType.LEGAL_DISCLOSURE, Severity.CRITICAL,
         "Health or risk claims require regulatory approval and disclosure.",
         ("MARKETING_CLAIMS", "§5.1")),  # not in the seed KB on purpose: shows "No source found"
    Rule("free_offer", re.compile(r"\bfree\b", re.I),
         IssueType.LEGAL_DISCLOSURE, Severity.HIGH,
         "'Free' offers must state their terms near the claim.",
         ("MARKETING_CLAIMS", "§3.2")),
    Rule("hype_words", re.compile(r"\b(?:revolutionary|game[- ]chang(?:er|ing)|disruptive)\b", re.I),
         IssueType.TONE_OF_VOICE, Severity.MEDIUM,
         "Hype vocabulary conflicts with the calm, confident brand voice.",
         ("BRAND_VOICE", "§4.2"), lambda m: "thoughtful"),
    Rule("urgency", re.compile(r"!{2,}|\bASAP\b|\bhurry\b", re.I),
         IssueType.TONE_OF_VOICE, Severity.LOW,
         "Urgency pressure and repeated exclamation marks read as aggressive.",
         ("BRAND_VOICE", "§4.5"),
         lambda m: "." if m.group(0).startswith("!") else ("soon" if m.group(0).lower() == "asap" else "explore")),
    Rule("brand_name", re.compile(r"(?<![\w/@.-])(?:InkLoom|Ink Loom|INKLOOM|inkloom)(?!\.\w|[\w/@-])"),
         IssueType.TERMINOLOGY, Severity.MEDIUM,
         "The product name is written incorrectly.",
         ("BRAND_VOICE", "§1.1"), lambda m: "Inkloom"),
    Rule("inclusive_language", re.compile(r"\b(?:guys|manpower|chairman|crazy|insane)\b", re.I),
         IssueType.INCLUSIVE_LANGUAGE, Severity.MEDIUM,
         "This term may exclude or stigmatise part of the audience.",
         ("BRAND_VOICE", "§6.1"),
         _sub({"guys": "everyone", "manpower": "workforce", "chairman": "chair", "crazy": "remarkable", "insane": "remarkable"})),
    Rule("click_here", re.compile(r"\bclick here\b", re.I),
         IssueType.ACCESSIBILITY, Severity.LOW,
         "Non-descriptive link text is hard to use with a screen reader.",
         ("BRAND_VOICE", "§7.3"), lambda m: "read the full details"),
]


def _match_case(original: str, new: str) -> str:
    """Keep a leading capital when the replaced text started with one (e.g. sentence start)."""
    if new and original[:1].isupper() and new[:1].islower() and not original.isupper():
        return new[:1].upper() + new[1:]
    return new


def _grounded(kb: KnowledgeBase, ref: Optional[tuple[str, str]]) -> tuple[Optional[Citation], Uncertainty]:
    chunk = kb.find_section(*ref) if ref else None
    if chunk:
        return citation_from_chunk(chunk), Uncertainty.RULE_BASED
    return None, Uncertainty.NO_SOURCE_FOUND


def run_rules(sentences: list[tuple[str, int, int]], kb: KnowledgeBase) -> list[Finding]:
    out: list[Finding] = []
    for sent, start, end in sentences:
        for rule in (kb.rules if kb.rules is not None else RULES):
            matches = list(rule.pattern.finditer(sent))
            if not matches:
                continue
            cite, unc = _grounded(kb, rule.guideline)
            edits = ()
            if rule.replace:
                pairs = [(m, rule.replace(m)) for m in matches]
                edits = tuple((m.start(), m.end(), _match_case(m.group(0), new)) for m, new in pairs if new is not None)
            out.append(Finding(rule.issue_type, rule.severity, sent, start, end, rule.explanation, unc,
                               cite, apply_edits(sent, edits) if edits else None, rule.advice, "rule", rule.id, edits))
    return out


# ---- approved facts -------------------------------------------------------------------
_NUM = re.compile(r"(?:[₹$€£]\s?)?\d[\d,]*(?:\.\d+)?(?:\s?%)?")
_GENERIC = {"price", "cost", "number", "count", "total", "rate", "amount", "value", "fact", "current"}


def _num_value(tok: str) -> str:
    return re.sub(r"[^\d.]", "", tok).rstrip(".")


def run_fact_checks(sentences: list[tuple[str, int, int]], kb: KnowledgeBase, warnings: list[str]) -> list[Finding]:
    out: list[Finding] = []
    today = date.today().isoformat()
    live: list[Fact] = []
    for f in kb.facts:
        if f.expires_at and f.expires_at[:10] < today:
            warnings.append(f"Approved fact '{f.title}' expired on {f.expires_at[:10]} and was not used.")
        else:
            live.append(f)
    for fact in live:
        keys = {t for t in tokenize(f"{fact.title} {fact.key.replace('_', ' ')}") if t not in _GENERIC}
        fact_nums = [m.group(0).strip() for m in _NUM.finditer(fact.value)]
        if not keys or not fact_nums:
            continue  # non-numeric facts are checked by the LLM step when enabled
        approved = {_num_value(n) for n in fact_nums}
        for sent, start, end in sentences:
            if not keys.issubset(set(tokenize(sent))):
                continue
            found = [m for m in _NUM.finditer(sent)]
            if not found or any(_num_value(m.group(0)) in approved for m in found):
                continue
            edits: tuple = ()
            if len(found) == 1 and len(fact_nums) == 1:
                m = found[0]
                edits = ((m.start(), m.end(), fact_nums[0]),)
            out.append(Finding(
                IssueType.FACT_MISMATCH, Severity.HIGH, sent, start, end,
                f"This figure does not match the approved value for '{fact.title}' ({fact.value}).",
                Uncertainty.RULE_BASED, citation_from_fact(fact),
                apply_edits(sent, edits) if edits else None, None, "fact", "fact:" + fact.key, edits))
    return out


# ---- accessibility ----------------------------------------------------------------------
_MD_IMG = re.compile(r"!\[\s*\]\([^)]*\)")
_HTML_IMG = re.compile(r"<img\b(?![^>]*\balt\s*=\s*[\"'][^\"']+[\"'])[^>]*>", re.I)


def run_accessibility(text: str, sentences: list[tuple[str, int, int]], kb: KnowledgeBase) -> list[Finding]:
    cite, unc = _grounded(kb, kb.accessibility_ref)
    limit = kb.sentence_limit
    out: list[Finding] = []
    for sent, start, end in sentences:
        n_words = len(words(sent))
        letters = [c for c in sent if c.isalpha()]
        if _MD_IMG.search(sent) or _HTML_IMG.search(sent):
            out.append(Finding(IssueType.ACCESSIBILITY, Severity.MEDIUM, sent, start, end,
                               "An image has no alt text, so screen-reader users cannot perceive it.",
                               unc, cite, None, None, "accessibility", "image_alt"))
        if kb.sentence_limit_mode == "each" and n_words > limit:
            out.append(Finding(IssueType.ACCESSIBILITY, Severity.LOW, sent, start, end,
                               f"This sentence has {n_words} words (limit {limit}); long sentences are hard to follow.",
                               unc, cite, None, "Split it into shorter sentences.", "accessibility", "long_sentence"))
        elif len(letters) >= 12 and n_words >= 3 and all(c.isupper() for c in letters):
            out.append(Finding(IssueType.ACCESSIBILITY, Severity.LOW, sent, start, end,
                               "Text in all capitals is harder to read and is often read letter by letter by screen readers.",
                               unc, cite, None, None, "accessibility", "all_caps"))
    if kb.sentence_limit_mode == "average" and sentences:
        counts = [len(words(s)) for s, _, _ in sentences]
        avg = sum(counts) / len(counts)
        if avg > limit:
            sent, start, end = sentences[counts.index(max(counts))]
            out.append(Finding(IssueType.ACCESSIBILITY, Severity.LOW, sent, start, end,
                               f"Average sentence length is {avg:.0f} words (limit {limit}); this is the longest sentence.",
                               unc, cite, None, "Split long sentences.", "accessibility", "avg_sentence"))
    return out


def run_pii(sentences: list[tuple[str, int, int]], kb: KnowledgeBase) -> list[Finding]:
    """Personal data in publishable copy. The finding never repeats the value itself."""
    cite, unc = _grounded(kb, kb.pii_ref)
    out: list[Finding] = []
    for sent, start, end in sentences:
        for label in find_pii(sent):
            out.append(Finding(IssueType.PII, Severity.HIGH, sent, start, end,
                               f"A personal {label} appears in publishable copy (value masked in reports).",
                               unc, cite, None, "Remove it and link to the official contact page instead.", "rule", "pii:" + label))
    return out


def reading_level_warning(text: str) -> Optional[str]:
    if len(words(text)) < 40:
        return None
    grade = flesch_kincaid_grade(text)
    if grade > MAX_GRADE:
        return f"Overall reading level is about grade {grade:.0f}; the guideline target is grade {MAX_GRADE:.0f} or below."
    return None


def apply_edits(sentence: str, edits: tuple) -> str:
    """Apply non-overlapping (start, end, new) edits to a sentence."""
    out, last = [], 0
    for s, e, new in sorted(edits):
        if s < last:
            continue
        out.append(sentence[last:s]); out.append(new); last = e
    out.append(sentence[last:])
    return "".join(out)
