import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError


DATABASE_URL = os.getenv(
	"DATABASE_URL",
	f"sqlite:///{(Path.home() / 'Downloads' / 'inkloom.db').as_posix()}",
)
engine = create_engine(
	DATABASE_URL,
	connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
	pool_pre_ping=True,
)
app = FastAPI(title="Brand Governance API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict[str, str]:
	try:
		with engine.connect() as connection:
			connection.execute(text("SELECT 1"))
	except SQLAlchemyError as exc:
		raise HTTPException(status_code=503, detail="Database connection failed") from exc
	return {"status": "ok", "database": "connected"}


@app.get("/db/tables")
def list_database_tables() -> dict[str, list[str]]:
	try:
		return {"tables": inspect(engine).get_table_names()}
	except SQLAlchemyError as exc:
		raise HTTPException(status_code=503, detail="Could not inspect database") from exc
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
import os
from pathlib import Path

# ... (your existing database setup and app initialization code) ...

app = FastAPI(title="Brand Governance API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    # ... (your existing health check code) ...
    return {"status": "ok", "database": "connected"}

@app.get("/db/tables")
def list_database_tables():
    # ... (your existing database tables code) ...
    return {"tables": []}


# ==========================================
# PASTE STEP 1 CODE RIGHT HERE:
# ==========================================

class ContentSubmissionCreate(BaseModel):
    title: str
    content_text: str
    content_type: str = "text"

class ContentSubmissionResponse(BaseModel):
    id: int
    title: str
    content_text: str
    status: str
    
    class Config:
        from_attributes = True

@app.post("/api/v1/content/upload", response_model=dict)
def upload_content(payload: ContentSubmissionCreate):
    return {
        "status": "success",
        "message": "Content submitted for brand governance review",
        "data": {
            "title": payload.title,
            "content_text": payload.content_text,
            "review_state": "PENDING_REVIEW"
        }
    }

@app.get("/api/v1/submissions/queue")
def get_review_queue():
    return {
        "queue": [],
        "total": 0
    }










