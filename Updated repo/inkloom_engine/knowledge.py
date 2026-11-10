"""Knowledge base: guideline sections + approved facts, with BM25 retrieval.

Sources: a JSON file (demo / role-4 seed data) or the database (see db_adapter.py).
Only the *current* version of each guideline and fact is used for checking.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from .models import Chunk, Fact

_STOP = set(
    "a an the and or of to in on for with is are was were be been it its this that these those at by as from "
    "we you your our not no do does can will should must may use used using any all each per than then".split()
)
_HEADING = re.compile(r"^\s*(?:#{1,6}\s*)?(§\s*[\w.]+)\s*[:.\-–—]?\s*(.*)$")
_MD_HEADING = re.compile(r"^\s*#{1,6}\s+(.+?)\s*$")


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9₹$%#]+", text.lower()) if t not in _STOP and len(t) > 1]


def split_sections(content: str) -> list[tuple[str, str]]:
    """Split guideline text into (section_id, text). Understands '§4.2 Title' and markdown headings;
    falls back to paragraphs so every guideline is still citable."""
    sections: list[tuple[str, list[str]]] = []
    for line in content.splitlines():
        m = _HEADING.match(line)
        if m:
            label = m.group(1).replace(" ", "")
            title = m.group(2).strip()
            sections.append((f"{label} {title}".strip(), []))
            continue
        m = _MD_HEADING.match(line)
        if m:
            sections.append((m.group(1).strip(), []))
            continue
        if sections:
            sections[-1][1].append(line)
        elif line.strip():
            sections.append(("Preamble", [line]))
    out = [(sid, "\n".join(body).strip()) for sid, body in sections if "\n".join(body).strip()]
    if len(out) <= 1 and len(content) > 600:  # unstructured long text -> paragraph chunks
        paras = [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]
        out = [(f"Paragraph {i + 1}", p) for i, p in enumerate(paras)]
    return out or [("Full text", content.strip())]


@dataclass
class KnowledgeBase:
    chunks: list[Chunk] = field(default_factory=list)
    facts: list[Fact] = field(default_factory=list)
    rules: Optional[list] = None                      # None -> built-in default rules (checks.RULES)
    accessibility_ref: tuple = ("BRAND_VOICE", "§7.3")  # (guideline code, section) cited for accessibility
    pii_ref: Optional[tuple] = None                   # section cited for personal-data findings, if any
    sentence_limit: int = 30
    sentence_limit_mode: str = "each"                 # "each" sentence, or the "average" over the document

    def __post_init__(self) -> None:
        self._index()

    # ---- construction -------------------------------------------------
    @classmethod
    def from_json(cls, path: str | Path) -> "KnowledgeBase":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeBase":
        chunks: list[Chunk] = []
        for g in data.get("guidelines", []):
            for s in g["sections"]:
                chunks.append(Chunk(g["code"], g["title"], str(g["version"]), g["effective_date"], s["id"], s["text"]))
        facts = [
            Fact(f["key"], f["title"], f["value"], str(f.get("version", "1")), f["effective_date"],
                 f.get("source_reference", ""), f.get("description", ""), f.get("expires_at"))
            for f in data.get("facts", [])
        ]
        return cls(chunks, facts)

    # ---- lookup -------------------------------------------------------
    def find_section(self, guideline_code: str, section_prefix: str) -> Optional[Chunk]:
        """Find a section by guideline code and section label (e.g. 'BRAND_VOICE', '§4.2')."""
        for c in self.chunks:
            if c.guideline_code == guideline_code and re.match(
                rf"^{re.escape(section_prefix)}(?![\w.])", c.section
            ):
                return c
        return None

    def version_labels(self) -> list[str]:
        seen = {f"{c.guideline_title} v{c.version}" for c in self.chunks}
        return sorted(seen)

    # ---- retrieval (BM25) ----------------------------------------------
    def _index(self) -> None:
        self._docs = [tokenize(f"{c.section} {c.text}") for c in self.chunks]
        self._df: Counter = Counter()
        for d in self._docs:
            self._df.update(set(d))
        self._avg = (sum(len(d) for d in self._docs) / len(self._docs)) if self._docs else 1.0

    def retrieve(self, query: str, k: int = 4) -> list[Chunk]:
        q = tokenize(query)
        n = len(self._docs)
        scored: list[tuple[float, int]] = []
        for i, d in enumerate(self._docs):
            tf = Counter(d)
            score = 0.0
            for t in q:
                if t in tf:
                    idf = math.log(1 + (n - self._df[t] + 0.5) / (self._df[t] + 0.5))
                    score += idf * tf[t] * 2.2 / (tf[t] + 1.2 * (0.25 + 0.75 * len(d) / self._avg))
            if score > 0:
                scored.append((score, i))
        scored.sort(reverse=True)
        return [self.chunks[i] for _, i in scored[:k]]

    def context_for(self, sentences: Iterable[str], per_sentence: int = 2, budget_chars: int = 9000) -> list[Chunk]:
        """Pick the guideline sections most relevant to the submitted text, within a size budget."""
        if sum(len(c.text) for c in self.chunks) <= budget_chars:
            return list(self.chunks)
        picked: dict[str, Chunk] = {}
        used = 0
        for s in sentences:
            for c in self.retrieve(s, per_sentence):
                if c.key not in picked and used + len(c.text) <= budget_chars:
                    picked[c.key] = c
                    used += len(c.text)
        return list(picked.values())
