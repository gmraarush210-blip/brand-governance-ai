"""
Inkloom Engine backend API. Owner: Aarush CU
Run: uvicorn main:app --reload     Docs: http://localhost:8000/docs
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import close_pool, get_pool, init_pool
from routes import approvals, insights, submissions


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_pool()
    try:
        yield
    finally:
        await close_pool()


app = FastAPI(title="Inkloom Engine API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    ).split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(submissions.router, prefix="/api/submissions", tags=["submissions"])
app.include_router(approvals.router, prefix="/api/approvals", tags=["approvals"])
app.include_router(insights.router, prefix="/api/insights", tags=["insights"])


@app.get("/api/health")
async def health() -> dict:
    await get_pool().fetchval("SELECT 1")
    return {"status": "ok"}
