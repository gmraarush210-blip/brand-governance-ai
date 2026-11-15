"""
Submission lifecycle: create, upload PDF, review, revise, fetch.
Owner: Aarush CU
"""
from typing import Optional

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from sqlalchemy import func

from database import (
    Comment,
    Decision,
    Finding,
    Revision,
    Submission,
    get_active_brand_pack,
    get_session,
    init_db,
)
from engine import ExtractionError, extract_pdf_text, run_review
from routes.auth import resolve_role

router = APIRouter()

MAX_PDF_BYTES = 10 * 1024 * 1024   # keep in sync with frontend UploadScreen.jsx
MAX_CHARS = 200_000


def _clean_content(content: str) -> str:
    if not content.strip():
        raise HTTPException(422, "content is empty")
    if len(content) > MAX_CHARS:
        raise HTTPException(413, f"content too long (max {MAX_CHARS} characters)")
    return content


def _row_to_dict(obj) -> dict:
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def _findings(session, sid: int, revision: int | None = None) -> list[dict]:
    if revision is None:
        max_ver = session.query(func.max(Revision.version)).filter(Revision.submission_id == sid).scalar()
        revision = max_ver
    rows = (
        session.query(Finding)
        .filter(Finding.submission_id == sid, Finding.revision == revision)
        .order_by(Finding.id)
        .all()
    )
    return [_row_to_dict(r) for r in rows]


@router.get("")
def list_submissions() -> dict:
    init_db()
    session = get_session()
    try:
        rows = session.query(Submission).order_by(Submission.id.desc()).limit(30).all()
        return {"items": [_row_to_dict(r) for r in rows]}
    finally:
        session.close()


@router.post("")
def create_submission(
    content: str = Form(...),
    title: str = Form("Untitled"),
    content_type: str = Form("text"),
    authorization: Optional[str] = Header(default=None),
) -> dict:
    init_db()
    role = resolve_role(authorization, "creator")
    content = _clean_content(content)
    title = title.strip()[:120] or "Untitled"
    session = get_session()
    try:
        sub = Submission(title=title, content_type=content_type, status="draft", created_by=role)
        session.add(sub)
        session.flush()
        rev = Revision(submission_id=sub.id, version=1, content=content, note="original")
        session.add(rev)
        session.commit()
        return {"id": sub.id, "status": "draft", "revision": 1}
    finally:
        session.close()


@router.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)) -> dict:
    data = await file.read(MAX_PDF_BYTES + 1)
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(413, "PDF is larger than 10 MB")
    if not data:
        raise HTTPException(422, "PDF extraction failed: file is empty")
    if not data.lstrip()[:5] == b"%PDF-":
        raise HTTPException(422, "PDF extraction failed: not a PDF file")
    try:
        text = extract_pdf_text(data)
    except ExtractionError as e:
        raise HTTPException(422, f"PDF extraction failed: {e}")
    return {"filename": file.filename, "text": text}


@router.get("/{submission_id}")
def get_submission(submission_id: int) -> dict:
    init_db()
    session = get_session()
    try:
        sub = session.query(Submission).filter(Submission.id == submission_id).first()
        if sub is None:
            raise HTTPException(404, "submission not found")
        revisions = [
            _row_to_dict(r)
            for r in session.query(Revision).filter(Revision.submission_id == submission_id).order_by(Revision.version).all()
        ]
        comments = [
            _row_to_dict(c)
            for c in session.query(Comment).filter(Comment.submission_id == submission_id).order_by(Comment.id).all()
        ]
        decisions = [
            _row_to_dict(d)
            for d in session.query(Decision).filter(Decision.submission_id == submission_id).order_by(Decision.id).all()
        ]
        return {
            "submission": _row_to_dict(sub),
            "revisions": revisions,
            "findings": _findings(session, submission_id),
            "comments": comments,
            "decisions": decisions,
        }
    finally:
        session.close()


@router.post("/{submission_id}/review")
def review_submission(submission_id: int) -> dict:
    init_db()
    session = get_session()
    try:
        rev = (
            session.query(Revision)
            .filter(Revision.submission_id == submission_id)
            .order_by(Revision.version.desc())
            .first()
        )
        if rev is None:
            raise HTTPException(404, "submission not found")
        active_pack = get_active_brand_pack()
        try:
            result = run_review(rev.content, pack=active_pack)
        except Exception as e:  # engine failure must never crash the API
            raise HTTPException(502, f"review engine failed: {e}")
        session.query(Finding).filter(Finding.submission_id == submission_id, Finding.revision == rev.version).delete()
        for f in result["findings"]:
            session.add(
                Finding(
                    submission_id=submission_id,
                    revision=rev.version,
                    issue_type=f["issue_type"],
                    severity=f["severity"],
                    excerpt=f["excerpt"],
                    explanation=f["explanation"],
                    cited_source=f["cited_source"],
                    suggested_fix=f["suggested_fix"],
                    uncertainty=f["uncertainty"],
                )
            )
        sub = session.query(Submission).filter(Submission.id == submission_id).first()
        if sub:
            sub.status = "reviewed"
        session.commit()
        return {
            "id": submission_id,
            "status": "reviewed",
            "revision": rev.version,
            "findings": _findings(session, submission_id, rev.version),
            "engine": result.get("engine"),
            "guideline_version": active_pack.get("version", "1.0"),
        }
    finally:
        session.close()


@router.post("/{submission_id}/revise")
def revise_submission(submission_id: int, content: str = Form(...), note: str = Form("")) -> dict:
    """Creator edits the draft. Earlier revisions are preserved."""
    init_db()
    content = _clean_content(content)
    session = get_session()
    try:
        max_ver = session.query(func.max(Revision.version)).filter(Revision.submission_id == submission_id).scalar()
        if max_ver is None:
            raise HTTPException(404, "submission not found")
        version = max_ver + 1
        session.add(Revision(submission_id=submission_id, version=version, content=content, note=note))
        sub = session.query(Submission).filter(Submission.id == submission_id).first()
        if sub:
            sub.status = "draft"
        session.commit()
        return {"id": submission_id, "revision": version, "status": "draft"}
    finally:
        session.close()
