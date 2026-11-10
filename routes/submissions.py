"""
Submission lifecycle: create, upload PDF, review, revise, fetch.
Owner: Aarush CU
"""
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from database import get_conn
from inkloom_engine import ExtractionError, extract_pdf_text, run_review

router = APIRouter()


def _findings(conn, sid: int, revision: int | None = None) -> list[dict]:
    if revision is None:
        row = conn.execute("SELECT MAX(version) v FROM revisions WHERE submission_id=?", (sid,)).fetchone()
        revision = row["v"]
    rows = conn.execute(
        "SELECT * FROM findings WHERE submission_id=? AND revision=? ORDER BY id", (sid, revision)
    ).fetchall()
    return [dict(r) for r in rows]


@router.post("")
def create_submission(
    content: str = Form(...),
    title: str = Form("Untitled"),
    content_type: str = Form("text"),
) -> dict:
    if not content.strip():
        raise HTTPException(422, "content is empty")
    conn = get_conn()
    try:
        cur = conn.execute("INSERT INTO submissions (title, content_type) VALUES (?, ?)", (title, content_type))
        sid = cur.lastrowid
        conn.execute("INSERT INTO revisions (submission_id, version, content, note) VALUES (?,1,?,?)",
                     (sid, content, "original"))
        conn.commit()
    finally:
        conn.close()
    return {"id": sid, "status": "draft", "revision": 1}


@router.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)) -> dict:
    data = await file.read()
    try:
        text = extract_pdf_text(data)
    except ExtractionError as e:
        raise HTTPException(422, f"PDF extraction failed: {e}")
    return {"filename": file.filename, "text": text}


@router.get("/{submission_id}")
def get_submission(submission_id: int) -> dict:
    conn = get_conn()
    try:
        sub = conn.execute("SELECT * FROM submissions WHERE id=?", (submission_id,)).fetchone()
        if sub is None:
            raise HTTPException(404, "submission not found")
        revisions = [dict(r) for r in conn.execute(
            "SELECT * FROM revisions WHERE submission_id=? ORDER BY version", (submission_id,))]
        comments = [dict(r) for r in conn.execute(
            "SELECT * FROM comments WHERE submission_id=? ORDER BY id", (submission_id,))]
        decisions = [dict(r) for r in conn.execute(
            "SELECT * FROM decisions WHERE submission_id=? ORDER BY id", (submission_id,))]
        return {
            "submission": dict(sub),
            "revisions": revisions,
            "findings": _findings(conn, submission_id),
            "comments": comments,
            "decisions": decisions,
        }
    finally:
        conn.close()


@router.post("/{submission_id}/review")
def review_submission(submission_id: int) -> dict:
    conn = get_conn()
    try:
        rev = conn.execute(
            "SELECT version, content FROM revisions WHERE submission_id=? ORDER BY version DESC LIMIT 1",
            (submission_id,),
        ).fetchone()
        if rev is None:
            raise HTTPException(404, "submission not found")
        try:
            result = run_review(rev["content"])
        except Exception as e:  # engine failure must never crash the API
            raise HTTPException(502, f"review engine failed: {e}")
        conn.execute("DELETE FROM findings WHERE submission_id=? AND revision=?", (submission_id, rev["version"]))
        for f in result["findings"]:
            conn.execute(
                "INSERT INTO findings (submission_id, revision, issue_type, severity, excerpt, explanation,"
                " cited_source, suggested_fix, uncertainty) VALUES (?,?,?,?,?,?,?,?,?)",
                (submission_id, rev["version"], f["issue_type"], f["severity"], f["excerpt"],
                 f["explanation"], f["cited_source"], f["suggested_fix"], f["uncertainty"]),
            )
        conn.execute("UPDATE submissions SET status='reviewed' WHERE id=?", (submission_id,))
        conn.commit()
        return {"id": submission_id, "status": "reviewed", "revision": rev["version"],
                "findings": _findings(conn, submission_id, rev["version"]), "engine": result.get("engine")}
    finally:
        conn.close()


@router.post("/{submission_id}/revise")
def revise_submission(submission_id: int, content: str = Form(...), note: str = Form("")) -> dict:
    """Creator edits the draft. Earlier revisions are preserved."""
    conn = get_conn()
    try:
        row = conn.execute("SELECT MAX(version) v FROM revisions WHERE submission_id=?", (submission_id,)).fetchone()
        if row["v"] is None:
            raise HTTPException(404, "submission not found")
        version = row["v"] + 1
        conn.execute("INSERT INTO revisions (submission_id, version, content, note) VALUES (?,?,?,?)",
                     (submission_id, version, content, note))
        conn.execute("UPDATE submissions SET status='draft' WHERE id=?", (submission_id,))
        conn.commit()
        return {"id": submission_id, "revision": version, "status": "draft"}
    finally:
        conn.close()
