"""
Inkloom Engine backend API. Owner: Aarush CU
Run: uvicorn main:app --reload     Docs: http://localhost:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routes import approvals, insights, submissions


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Inkloom Engine API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(submissions.router, prefix="/api/submissions", tags=["submissions"])
app.include_router(approvals.router, prefix="/api/approvals", tags=["approvals"])
app.include_router(insights.router, prefix="/api/insights", tags=["insights"])


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
