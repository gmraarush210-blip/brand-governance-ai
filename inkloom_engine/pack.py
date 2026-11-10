"""Load a knowledge base from either file format.

* native format  : data/seed_knowledge.json (guidelines[].sections[], facts[].key/value)
* brand-pack     : data/fictional_brand_pack.json used by the team repo
                   (brand, terminology.avoid/preferred, guidelines[].id/section/text, facts[].claim/value)

For a brand pack the rules are generated FROM the pack (avoid-list, brand name, facts), so the same
engine enforces whichever brand's data it is given. Section numbers follow the pack's own scheme:
2.1 claims, 2.2 outcome language/terminology, 3.1 brand name, 4.1 personal data, 5.1 accessibility.
A rule whose section is missing from the pack is still reported, as "No source found".
"""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

from .checks import Rule
from .knowledge import KnowledgeBase
from .models import Chunk, Fact, IssueType, Severity

CODE = "BRAND_PACK"
ABSOLUTE_CLAIMS = (
    r"fastest in the world", r"\bzero (?:errors|defects|risk|bugs)\b", r"\b100\s?%",
    r"\bbest in (?:the )?(?:world|class)\b", r"\bnumber one\b",
)


def default_pack_path() -> Path:
    env = os.getenv("INKLOOM_PACK")
    return Path(env) if env else Path(__file__).resolve().parent.parent / "data" / "fictional_brand_pack.json"


def kb_from_pack(pack: dict) -> KnowledgeBase:
    brand, ver, date = pack["brand"], str(pack["version"]), pack["date"]
    title = f"{brand} Brand Pack"
    chunks = [Chunk(CODE, title, ver, date, "§" + g["section"].lstrip("§"), g["text"]) for g in pack.get("guidelines", [])]
    facts = [Fact(f["claim"].upper(), f["claim"].replace("_", " ").title(), str(f["value"]), ver, date,
                  f"{title}, approved facts", expires_at=f.get("expires_at")) for f in pack.get("facts", [])]

    term = pack.get("terminology", {})
    avoid = sorted(term.get("avoid", []), key=len, reverse=True)
    preferred = {k.lower(): v for k, v in term.get("preferred", {}).items()}
    rules: list[Rule] = []
    if avoid:
        rules.append(Rule(
            "pack_terminology", re.compile(r"\b(?:" + "|".join(re.escape(t) for t in avoid) + r")\b", re.I),
            IssueType.TERMINOLOGY, Severity.HIGH,
            "This term is on the brand pack's avoid list because it implies a guaranteed or curative outcome.",
            (CODE, "§2.2"), lambda m: preferred.get(m.group(0).lower()),
            'Use plain, supportable wording such as "supports" or "designed to help".'))
    rules.append(Rule(
        "pack_absolute_claim", re.compile("|".join(ABSOLUTE_CLAIMS), re.I),
        IssueType.CLAIMS_COMPLIANCE, Severity.HIGH,
        "Absolute performance claim. The approved fact sheet has no verified entry for it.",
        (CODE, "§2.1"), None,
        'Soften it (e.g. "built for speed", "designed to help reduce errors") or add a verified fact.'))
    short = brand.split()[0]
    wrong = sorted({short.upper(), short.lower()} - {short}, key=len)
    if wrong:
        rules.append(Rule(
            "pack_brand_name", re.compile(r"(?<![\w/@.-])(?:" + "|".join(map(re.escape, wrong)) + r")(?!\.\w|[\w/@-])"),
            IssueType.TERMINOLOGY, Severity.LOW, f'The brand name is written incorrectly; use "{short}".',
            (CODE, "§3.1"), lambda m: short))

    return KnowledgeBase(chunks, facts, rules=rules, accessibility_ref=(CODE, "§5.1"),
                         pii_ref=(CODE, "§4.1"), sentence_limit=25, sentence_limit_mode="average")


def load_kb(path: Optional[str | Path] = None) -> KnowledgeBase:
    p = Path(path) if path else default_pack_path()
    return _load(str(p), p.stat().st_mtime)


@lru_cache(maxsize=4)
def _load(path: str, _mtime: float) -> KnowledgeBase:  # mtime in the key => edits are picked up
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if "brand" in data and "terminology" in data:
        return kb_from_pack(data)
    return KnowledgeBase.from_dict(data)
