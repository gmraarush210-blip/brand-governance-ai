"""
Inkloom Engine backend API. Owner: Aarush CU
Run: uvicorn main:app --reload     Docs: http://localhost:8000/docs
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import db_backend_info, init_db
from routes import approvals, auth, guidelines, insights, submissions


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Inkloom Engine API", version="0.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    ).split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(guidelines.router, prefix="/api/guidelines", tags=["guidelines"])
app.include_router(submissions.router, prefix="/api/submissions", tags=["submissions"])
app.include_router(approvals.router, prefix="/api/approvals", tags=["approvals"])
app.include_router(insights.router, prefix="/api/insights", tags=["insights"])


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": "0.3.0", **db_backend_info()}
