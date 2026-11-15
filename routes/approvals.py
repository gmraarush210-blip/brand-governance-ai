"""
Role-based finding actions, comments, queue and approval decisions.
Owner: Aarush CU
Roles: creator, manager, reviewer. High/critical findings need manager or reviewer.
There is NO auto-publish: approval only records a human decision.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import get_pool

router = APIRouter()

ROLES = {"creator", "manager", "reviewer"}
HIGH_RISK = {"high", "critical"}


class FindingAction(BaseModel):
    state: str                 # accepted | rejected | open
    role: str = "creator"
    comment: str = ""
    reason: str = ""           # rejection reason (feeds insights)


class Decision(BaseModel):
    decision: str              # approve | request_changes | escalate
    role: str
    note: str = ""


def _check_role(role: str) -> None:
    if role not in ROLES:
        raise HTTPException(400, f"unknown role '{role}'")


@router.get("/queue")
async def queue(role: str = "reviewer") -> dict:
    _check_role(role)
    rows = await get_pool().fetch(
        "SELECT id, submission_id, issue_type, severity, state, excerpt FROM findings WHERE state = 'open'"
    )
    items = [dict(row) for row in rows]
    if role in {"manager", "reviewer"}:
        items = [item for item in items if item["severity"] in HIGH_RISK]
    return {"role": role, "items": items}


@router.post("/findings/{finding_id}")
async def act_on_finding(finding_id: int, action: FindingAction) -> dict:
    _check_role(action.role)
    if action.state not in {"accepted", "rejected", "open"}:
        raise HTTPException(400, "invalid state")

    async with get_pool().acquire() as conn:
        async with conn.transaction():
            finding = await conn.fetchrow(
                "SELECT * FROM findings WHERE id = $1 FOR UPDATE",
                finding_id,
            )
            if finding is None:
                raise HTTPException(404, "finding not found")
            if finding["severity"] in HIGH_RISK and action.role == "creator":
                raise HTTPException(403, "high-risk findings must be resolved by a manager or reviewer")
            await conn.execute(
                "UPDATE findings SET state = $1, rejection_reason = $2, resolved_by = $3 WHERE id = $4",
                action.state,
                action.reason if action.state == "rejected" else "",
                action.role,
                finding_id,
            )
            if action.comment:
                await conn.execute(
                    "INSERT INTO comments (submission_id, finding_id, author_role, body) VALUES ($1, $2, $3, $4)",
                    finding["submission_id"],
                    finding_id,
                    action.role,
                    action.comment,
                )
    return {"id": finding_id, "state": action.state}


@router.post("/submissions/{submission_id}/decision")
async def decide(submission_id: int, d: Decision) -> dict:
    _check_role(d.role)
    if d.decision not in {"approve", "request_changes", "escalate"}:
        raise HTTPException(400, "invalid decision")
    if d.role == "creator":
        raise HTTPException(403, "only a manager or reviewer can record an approval decision")

    status = {"approve": "approved", "request_changes": "changes_requested", "escalate": "escalated"}[d.decision]
    async with get_pool().acquire() as conn:
        async with conn.transaction():
            submission = await conn.fetchrow(
                "SELECT id FROM submissions WHERE id = $1 FOR UPDATE",
                submission_id,
            )
            if submission is None:
                raise HTTPException(404, "submission not found")
            if d.decision == "approve":
                version = await conn.fetchval(
                    "SELECT MAX(version) FROM revisions WHERE submission_id = $1",
                    submission_id,
                )
                open_high = 0
                if version is not None:
                    open_high = await conn.fetchval(
                        "SELECT COUNT(*) FROM findings WHERE submission_id = $1 AND revision = $2 "
                        "AND state = 'open' AND severity IN ('high', 'critical')",
                        submission_id,
                        version,
                    )
                if open_high:
                    raise HTTPException(409, f"{open_high} high-risk finding(s) still open")
            await conn.execute(
                "UPDATE submissions SET status = $1 WHERE id = $2",
                status,
                submission_id,
            )
            await conn.execute(
                "INSERT INTO decisions (submission_id, role, decision, note) VALUES ($1, $2, $3, $4)",
                submission_id,
                d.role,
                d.decision,
                d.note,
            )
    return {"id": submission_id, "status": status}
