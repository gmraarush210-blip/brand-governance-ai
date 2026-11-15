"""
Descriptive insights: recurring issue types, rejection patterns, guideline gaps.
No per-employee ranking. Owner: Aarush CU
"""
from fastapi import APIRouter
from sqlalchemy import func

from database import Finding, get_session, init_db

router = APIRouter()


@router.get("")
def insights() -> dict:
    init_db()
    session = get_session()
    try:
        by_type = [
            {"issue_type": itype, "count": cnt}
            for itype, cnt in session.query(Finding.issue_type, func.count(Finding.id))
            .group_by(Finding.issue_type)
            .order_by(func.count(Finding.id).desc())
            .all()
        ]
        rejected = [
            {"cited_source": src, "rejections": cnt}
            for src, cnt in session.query(Finding.cited_source, func.count(Finding.id))
            .filter(Finding.state == "rejected")
            .group_by(Finding.cited_source)
            .order_by(func.count(Finding.id).desc())
            .all()
        ]
        no_source = (
            session.query(func.count(Finding.id))
            .filter(Finding.cited_source.like("No source found%"))
            .scalar()
            or 0
        )
        unresolved = session.query(func.count(Finding.id)).filter(Finding.state == "open").scalar() or 0
        return {
            "by_issue_type": by_type,
            "frequently_rejected_rules": rejected,
            "findings_without_source": no_source,
            "unresolved": unresolved,
        }
    finally:
        session.close()
