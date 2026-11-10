"""
Descriptive insights: recurring issue types, rejection patterns, guideline gaps.
No per-employee ranking. Owner: Aarush CU
"""
from fastapi import APIRouter

from database import get_conn

router = APIRouter()


@router.get("")
def insights() -> dict:
    conn = get_conn()
    try:
        by_type = [dict(r) for r in conn.execute(
            "SELECT issue_type, COUNT(*) AS count FROM findings GROUP BY issue_type ORDER BY count DESC")]
        rejected = [dict(r) for r in conn.execute(
            "SELECT cited_source, COUNT(*) AS rejections FROM findings WHERE state='rejected'"
            " GROUP BY cited_source ORDER BY rejections DESC")]
        no_source = conn.execute(
            "SELECT COUNT(*) c FROM findings WHERE cited_source LIKE 'No source found%'").fetchone()["c"]
        unresolved = conn.execute("SELECT COUNT(*) c FROM findings WHERE state='open'").fetchone()["c"]
        return {"by_issue_type": by_type, "frequently_rejected_rules": rejected,
                "findings_without_source": no_source, "unresolved": unresolved}
    finally:
        conn.close()
