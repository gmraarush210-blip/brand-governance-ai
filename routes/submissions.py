"""
Submission lifecycle: create, upload PDF, review, revise, fetch.
Owner: Aarush CU
"""
import asyncio

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from database import get_pool
from engine import ExtractionError, extract_pdf_text, run_review

router = APIRouter()

MAX_PDF_BYTES = 10 * 1024 * 1024   # keep in sync with frontend UploadScreen.jsx
MAX_CHARS = 200_000


def _clean_content(content: str) -> str:
    if not content.strip():
        raise HTTPException(422, "content is empty")
    if len(content) > MAX_CHARS:
        raise HTTPException(413, f"content too long (max {MAX_CHARS} characters)")
    return content


async def _findings(conn, sid: int, revision: int | None = None) -> list[dict]:
    if revision is None:
        revision = await conn.fetchval(
            "SELECT MAX(version) FROM revisions WHERE submission_id = $1", sid
        )
    if revision is None:
        return []
    rows = await conn.fetch(
        "SELECT * FROM findings WHERE submission_id = $1 AND revision = $2 ORDER BY id",
        sid,
        revision,
    )
    return [dict(row) for row in rows]


@router.post("")
async def create_submission(
    content: str = Form(...),
    title: str = Form("Untitled"),
    content_type: str = Form("text"),
) -> dict:
    content = _clean_content(content)
    title = title.strip()[:120] or "Untitled"
    async with get_pool().acquire() as conn:
        async with conn.transaction():
            submission = await conn.fetchrow(
                "INSERT INTO submissions (title, content_type) VALUES ($1, $2) RETURNING id",
                title,
                content_type,
            )
            sid = submission["id"]
            await conn.execute(
                "INSERT INTO revisions (submission_id, version, content, note) VALUES ($1, 1, $2, $3)",
                sid,
                content,
                "original",
            )
    return {"id": sid, "status": "draft", "revision": 1}


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
async def get_submission(submission_id: int) -> dict:
    async with get_pool().acquire() as conn:
        sub = await conn.fetchrow("SELECT * FROM submissions WHERE id = $1", submission_id)
        if sub is None:
            raise HTTPException(404, "submission not found")
        revisions = [
            dict(row)
            for row in await conn.fetch(
                "SELECT * FROM revisions WHERE submission_id = $1 ORDER BY version",
                submission_id,
            )
        ]
        comments = [
            dict(row)
            for row in await conn.fetch(
                "SELECT * FROM comments WHERE submission_id = $1 ORDER BY id",
                submission_id,
            )
        ]
        decisions = [
            dict(row)
            for row in await conn.fetch(
                "SELECT * FROM decisions WHERE submission_id = $1 ORDER BY id",
                submission_id,
            )
        ]
        findings = await _findings(conn, submission_id)
    return {
        "submission": dict(sub),
        "revisions": revisions,
        "findings": findings,
        "comments": comments,
        "decisions": decisions,
    }


@router.post("/{submission_id}/review")
async def review_submission(submission_id: int) -> dict:
    async with get_pool().acquire() as conn:
        rev = await conn.fetchrow(
            "SELECT version, content FROM revisions WHERE submission_id = $1 ORDER BY version DESC LIMIT 1",
            submission_id,
        )
        if rev is None:
            raise HTTPException(404, "submission not found")
        try:
            result = await asyncio.to_thread(run_review, rev["content"])
        except Exception as e:  # engine failure must never crash the API
            raise HTTPException(502, f"review engine failed: {e}")

        async with conn.transaction():
            await conn.execute(
                "DELETE FROM findings WHERE submission_id = $1 AND revision = $2",
                submission_id,
                rev["version"],
            )
            finding_values = [
                (
                    submission_id,
                    rev["version"],
                    finding["issue_type"],
                    finding["severity"],
                    finding["excerpt"],
                    finding["explanation"],
                    finding["cited_source"],
                    finding["suggested_fix"],
                    finding["uncertainty"],
                )
                for finding in result["findings"]
            ]
            if finding_values:
                await conn.executemany(
                    "INSERT INTO findings (submission_id, revision, issue_type, severity, excerpt, explanation, "
                    "cited_source, suggested_fix, uncertainty) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
                    finding_values,
                )
            await conn.execute(
                "UPDATE submissions SET status = 'reviewed' WHERE id = $1",
                submission_id,
            )
        findings = await _findings(conn, submission_id, rev["version"])
    return {
        "id": submission_id,
        "status": "reviewed",
        "revision": rev["version"],
        "findings": findings,
        "engine": result.get("engine"),
    }


@router.post("/{submission_id}/revise")
async def revise_submission(submission_id: int, content: str = Form(...), note: str = Form("")) -> dict:
    """Creator edits the draft. Earlier revisions are preserved."""
    content = _clean_content(content)
    async with get_pool().acquire() as conn:
        async with conn.transaction():
            submission = await conn.fetchrow(
                "SELECT id FROM submissions WHERE id = $1 FOR UPDATE",
                submission_id,
            )
            if submission is None:
                raise HTTPException(404, "submission not found")
            version = await conn.fetchval(
                "SELECT MAX(version) FROM revisions WHERE submission_id = $1",
                submission_id,
            )
            if version is None:
                raise HTTPException(404, "submission not found")
            version += 1
            await conn.execute(
                "INSERT INTO revisions (submission_id, version, content, note) VALUES ($1, $2, $3, $4)",
                submission_id,
                version,
                content,
                note,
            )
            await conn.execute(
                "UPDATE submissions SET status = 'draft' WHERE id = $1",
                submission_id,
            )
    return {"id": submission_id, "revision": version, "status": "draft"}
