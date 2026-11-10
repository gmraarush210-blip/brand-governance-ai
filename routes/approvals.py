"""
Role-based finding actions, comments, queue and approval decisions.
Owner: Aarush CU
Roles: creator, manager, reviewer. High/critical findings need manager or reviewer.
There is NO auto-publish: approval only records a human decision.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import get_conn

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
def queue(role: str = "reviewer") -> dict:
    _check_role(role)
    conn = get_conn()
    try:
        # Retrieve open findings strictly from the latest revision of each submission
        rows = conn.execute(
            """
            SELECT f.id, f.submission_id, f.issue_type, f.severity, f.state, f.excerpt 
            FROM findings f
            JOIN (
                SELECT submission_id, MAX(version) as max_rev 
                FROM revisions 
                GROUP BY submission_id
            ) r ON f.submission_id = r.submission_id AND f.revision = r.max_rev
            WHERE f.state='open'
            """
        ).fetchall()
        items = [dict(r) for r in rows]
        if role in {"manager", "reviewer"}:
            items = [i for i in items if i["severity"] in HIGH_RISK]
        return {"role": role, "items": items}
    finally:
        conn.close()


@router.post("/findings/{finding_id}")
def act_on_finding(finding_id: int, action: FindingAction) -> dict:
    _check_role(action.role)
    if action.state not in {"accepted", "rejected", "open"}:
        raise HTTPException(400, "invalid state")
    conn = get_conn()
    try:
        f = conn.execute("SELECT * FROM findings WHERE id=?", (finding_id,)).fetchone()
        if f is None:
            raise HTTPException(404, "finding not found")
        if f["severity"] in HIGH_RISK and action.role == "creator":
            raise HTTPException(403, "high-risk findings must be resolved by a manager or reviewer")
        conn.execute(
            "UPDATE findings SET state=?, rejection_reason=?, resolved_by=? WHERE id=?",
            (action.state, action.reason if action.state == "rejected" else "", action.role, finding_id),
        )
        if action.comment:
            conn.execute(
                "INSERT INTO comments (submission_id, finding_id, author_role, body) VALUES (?,?,?,?)",
                (f["submission_id"], finding_id, action.role, action.comment),
            )
        conn.commit()
        return {"id": finding_id, "state": action.state}
    finally:
        conn.close()


@router.post("/submissions/{submission_id}/decision")
def decide(submission_id: int, d: Decision) -> dict:
    _check_role(d.role)
    if d.decision not in {"approve", "request_changes", "escalate"}:
        raise HTTPException(400, "invalid decision")
    if d.role == "creator":
        raise HTTPException(403, "only a manager or reviewer can record an approval decision")
    conn = get_conn()
    try:
        sub = conn.execute("SELECT * FROM submissions WHERE id=?", (submission_id,)).fetchone()
        if sub is None:
            raise HTTPException(404, "submission not found")
        
        # Block decisions if already approved
        if sub["status"] == "approved":
            raise HTTPException(409, "submission is already approved")

        # Check whether the latest revision has been reviewed
        latest_rev = conn.execute(
            "SELECT MAX(version) v FROM revisions WHERE submission_id=?",
            (submission_id,),
        ).fetchone()["v"]

        if sub["reviewed_revision"] != latest_rev:
            raise HTTPException(409, "latest revision has not been reviewed")

        if d.decision == "approve":
            open_high = conn.execute(
                "SELECT COUNT(*) c FROM findings WHERE submission_id=? AND revision=? AND state='open'"
                " AND severity IN ('high','critical')", (submission_id, latest_rev)).fetchone()["c"]
            if open_high:
                raise HTTPException(409, f"{open_high} high-risk finding(s) still open")

        status = {"approve": "approved", "request_changes": "changes_requested", "escalate": "escalated"}[d.decision]
        conn.execute("UPDATE submissions SET status=? WHERE id=?", (status, submission_id))
        conn.execute("INSERT INTO decisions (submission_id, role, decision, note) VALUES (?,?,?,?)",
                     (submission_id, d.role, d.decision, d.note))
        conn.commit()
        return {"id": submission_id, "status": status}
    finally:
        conn.close()
