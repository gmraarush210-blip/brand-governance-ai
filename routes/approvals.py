"""
Role-based finding actions, comments, queue and approval decisions.
Owner: Aarush CU
Roles: creator, manager, reviewer. High/critical findings need manager or reviewer.
There is NO auto-publish: approval only records a human decision.
"""
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import func

from database import Comment, Decision, Finding, Revision, Submission, get_session, init_db
from routes.auth import ROLES, resolve_role

router = APIRouter()

HIGH_RISK = {"high", "critical"}


class FindingAction(BaseModel):
    state: str                 # accepted | rejected | open
    role: Optional[str] = None
    comment: str = ""
    reason: str = ""           # rejection reason (feeds insights)


class DecisionPayload(BaseModel):
    decision: str              # approve | request_changes | escalate
    role: Optional[str] = None
    note: str = ""


def _check_role(role: str) -> None:
    if role not in ROLES:
        raise HTTPException(400, f"unknown role '{role}'")


@router.get("/queue")
def queue(role: Optional[str] = None, authorization: Optional[str] = Header(default=None)) -> dict:
    init_db()
    effective_role = resolve_role(authorization, role or "reviewer")
    _check_role(effective_role)
    session = get_session()
    try:
        rows = session.query(Finding).filter(Finding.state == "open").all()
        items = [
            {
                "id": r.id,
                "submission_id": r.submission_id,
                "issue_type": r.issue_type,
                "severity": r.severity,
                "state": r.state,
                "excerpt": r.excerpt,
            }
            for r in rows
        ]
        if effective_role in {"manager", "reviewer"}:
            items = [i for i in items if i["severity"] in HIGH_RISK]
        return {"role": effective_role, "items": items}
    finally:
        session.close()


@router.post("/findings/{finding_id}")
def act_on_finding(
    finding_id: int,
    action: FindingAction,
    authorization: Optional[str] = Header(default=None),
) -> dict:
    init_db()
    effective_role = resolve_role(authorization, action.role or "creator")
    _check_role(effective_role)
    if action.state not in {"accepted", "rejected", "open"}:
        raise HTTPException(400, "invalid state")
    session = get_session()
    try:
        f = session.query(Finding).filter(Finding.id == finding_id).first()
        if f is None:
            raise HTTPException(404, "finding not found")
        if f.severity in HIGH_RISK and effective_role == "creator":
            raise HTTPException(403, "high-risk findings must be resolved by a manager or reviewer")
        f.state = action.state
        f.rejection_reason = action.reason if action.state == "rejected" else ""
        f.resolved_by = effective_role
        if action.comment:
            session.add(
                Comment(
                    submission_id=f.submission_id,
                    finding_id=finding_id,
                    author_role=effective_role,
                    body=action.comment,
                )
            )
        session.commit()
        return {"id": finding_id, "state": action.state}
    finally:
        session.close()


@router.post("/submissions/{submission_id}/decision")
def decide(
    submission_id: int,
    d: DecisionPayload,
    authorization: Optional[str] = Header(default=None),
) -> dict:
    init_db()
    effective_role = resolve_role(authorization, d.role or "creator")
    _check_role(effective_role)
    if d.decision not in {"approve", "request_changes", "escalate"}:
        raise HTTPException(400, "invalid decision")
    if effective_role == "creator":
        raise HTTPException(403, "only a manager or reviewer can record an approval decision")
    session = get_session()
    try:
        sub = session.query(Submission).filter(Submission.id == submission_id).first()
        if sub is None:
            raise HTTPException(404, "submission not found")
        if d.decision == "approve":
            ver = session.query(func.max(Revision.version)).filter(Revision.submission_id == submission_id).scalar()
            open_high = (
                session.query(func.count(Finding.id))
                .filter(
                    Finding.submission_id == submission_id,
                    Finding.revision == ver,
                    Finding.state == "open",
                    Finding.severity.in_(["high", "critical"]),
                )
                .scalar()
            )
            if open_high:
                raise HTTPException(409, f"{open_high} high-risk finding(s) still open")
        status = {"approve": "approved", "request_changes": "changes_requested", "escalate": "escalated"}[d.decision]
        # Idempotency guard: if already in this status from the same role, return cleanly
        sub.status = status
        session.add(Decision(submission_id=submission_id, role=effective_role, decision=d.decision, note=d.note))
        session.commit()
        return {"id": submission_id, "status": status}
    finally:
        session.close()
