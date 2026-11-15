"""
Descriptive insights: recurring issue types, rejection patterns, guideline gaps.
No per-employee ranking. Owner: Aarush CU
"""
from fastapi import APIRouter

from database import get_pool

router = APIRouter()


@router.get("")
async def insights() -> dict:
    pool = get_pool()
    by_type = [
        dict(row)
        for row in await pool.fetch(
            "SELECT issue_type, COUNT(*) AS count FROM findings GROUP BY issue_type ORDER BY count DESC"
        )
    ]
    rejected = [
        dict(row)
        for row in await pool.fetch(
            "SELECT cited_source, COUNT(*) AS rejections FROM findings WHERE state = 'rejected' "
            "GROUP BY cited_source ORDER BY rejections DESC"
        )
    ]
    no_source = await pool.fetchval(
        "SELECT COUNT(*) FROM findings WHERE cited_source LIKE 'No source found%'"
    )
    unresolved = await pool.fetchval("SELECT COUNT(*) FROM findings WHERE state = 'open'")
    return {
        "by_issue_type": by_type,
        "frequently_rejected_rules": rejected,
        "findings_without_source": no_source,
        "unresolved": unresolved,
    }
