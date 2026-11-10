"""Plain data types for the Inkloom review engine (no database or web dependencies)."""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional


# Values deliberately mirror the enums in Aarush's Brand_Governance_Schema_Fixed.py
# so the DB adapter can map them by value.
class Severity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @property
    def rank(self) -> int:
        return ["LOW", "MEDIUM", "HIGH", "CRITICAL"].index(self.value)


class Uncertainty(str, enum.Enum):
    SOURCE_FOUND = "SOURCE_FOUND"      # model finding whose citation was verified against the knowledge base
    NO_SOURCE_FOUND = "NO_SOURCE_FOUND"  # we could not cite approved evidence
    MODEL_UNCERTAIN = "MODEL_UNCERTAIN"  # the model itself reported low confidence
    RULE_BASED = "RULE_BASED"          # deterministic rule matched; citation verified


class IssueType(str, enum.Enum):
    CLAIMS_COMPLIANCE = "CLAIMS_COMPLIANCE"
    TONE_OF_VOICE = "TONE_OF_VOICE"
    TERMINOLOGY = "TERMINOLOGY"
    INCLUSIVE_LANGUAGE = "INCLUSIVE_LANGUAGE"
    LEGAL_DISCLOSURE = "LEGAL_DISCLOSURE"
    FORMATTING = "FORMATTING"
    ACCESSIBILITY = "ACCESSIBILITY"
    FACT_MISMATCH = "FACT_MISMATCH"
    PII = "PII"


@dataclass(frozen=True)
class Chunk:
    """One citable section of a guideline version."""
    guideline_code: str
    guideline_title: str
    version: str
    effective_date: str  # ISO date
    section: str
    text: str
    guideline_id: Optional[int] = None  # DB ids, filled when loaded from the database
    version_id: Optional[int] = None

    @property
    def key(self) -> str:
        return f"{self.guideline_code}|{self.section}"


@dataclass(frozen=True)
class Fact:
    """The current approved value of a named fact."""
    key: str
    title: str
    value: str
    version: str
    effective_date: str
    source_reference: str = ""
    description: str = ""
    expires_at: Optional[str] = None
    fact_id: Optional[int] = None
    version_id: Optional[int] = None


@dataclass(frozen=True)
class Citation:
    kind: str  # "guideline" | "fact"
    name: str
    section: str  # section id, or the fact key
    version: str
    effective_date: str
    excerpt: str
    guideline_id: Optional[int] = None
    version_id: Optional[int] = None  # guideline version id OR fact version id, by `kind`

    @property
    def reference(self) -> str:
        sec = f" {self.section}" if self.section else ""
        return f"{self.name} v{self.version}{sec}".strip()


@dataclass
class Finding:
    issue_type: IssueType
    severity: Severity
    flagged_text: str            # exact sentence from the submitted content
    start: int                   # offsets of flagged_text in the submitted content
    end: int
    explanation: str
    uncertainty: Uncertainty
    citation: Optional[Citation] = None
    suggested_fix: Optional[str] = None  # a proposal only; never applied automatically
    advice: Optional[str] = None  # guidance when no safe replacement exists (never auto-applied)
    origin: str = "rule"         # rule | fact | accessibility | llm
    rule_id: str = ""            # which check produced it (keeps distinct checks from merging)
    # (start, end, replacement) offsets relative to flagged_text, used to compose fixes
    edits: tuple = field(default_factory=tuple, repr=False)


@dataclass
class ReviewResult:
    findings: list[Finding]
    mode: str                    # "rules" or "rules+llm"
    warnings: list[str] = field(default_factory=list)
    knowledge_versions: list[str] = field(default_factory=list)
    disclosure: str = ""
