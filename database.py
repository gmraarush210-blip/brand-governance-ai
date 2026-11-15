"""
Persistence layer (PostgreSQL + SQLite dual backend via SQLAlchemy). Owner: Aarush CU
Tables: submissions, revisions, findings, comments, decisions, guideline_packs, users.
Original text is never overwritten: every edit is a new revision.
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import Column, Integer, String, Text, create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

DEFAULT_PACK_PATH = Path(__file__).resolve().parent / "data" / "fictional_brand_pack.json"
Base = declarative_base()


class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False, default="Untitled")
    content_type = Column(String(64), nullable=False, default="text")
    status = Column(String(64), nullable=False, default="draft")
    created_by = Column(String(120), nullable=False, default="creator")
    created_at = Column(String(64), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())


class Revision(Base):
    __tablename__ = "revisions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, nullable=False, index=True)
    version = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    note = Column(Text, default="")
    created_at = Column(String(64), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())


class Finding(Base):
    __tablename__ = "findings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, nullable=False, index=True)
    revision = Column(Integer, nullable=False, default=1)
    issue_type = Column(String(120), nullable=False)
    severity = Column(String(32), nullable=False)
    excerpt = Column(Text, default="")
    explanation = Column(Text, default="")
    cited_source = Column(Text, default="")
    suggested_fix = Column(Text, default="")
    uncertainty = Column(Text, default="")
    state = Column(String(32), nullable=False, default="open")
    rejection_reason = Column(Text, default="")
    resolved_by = Column(String(120), default="")


class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, nullable=False, index=True)
    finding_id = Column(Integer, nullable=True)
    author_role = Column(String(64), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(String(64), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())


class Decision(Base):
    __tablename__ = "decisions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, nullable=False, index=True)
    role = Column(String(64), nullable=False)
    decision = Column(String(64), nullable=False)
    note = Column(Text, default="")
    created_at = Column(String(64), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())


class GuidelinePack(Base):
    __tablename__ = "guideline_packs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    brand = Column(String(120), nullable=False)
    version = Column(String(64), nullable=False)
    date = Column(String(64), nullable=False)
    pack_json = Column(Text, nullable=False)
    is_active = Column(Integer, nullable=False, default=1)
    updated_by = Column(String(120), nullable=False, default="system")
    created_at = Column(String(64), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())


class UserAccount(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(180), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    role = Column(String(32), nullable=False)
    password_hash = Column(String(256), nullable=False)
    created_at = Column(String(64), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())


_engines: dict[str, Any] = {}


def get_database_url() -> str:
    db_url = os.getenv("DATABASE_URL", "").strip()
    if db_url:
        if db_url.startswith("postgres://"):
            db_url = "postgresql://" + db_url[len("postgres://"):]
        return db_url
    db_path = os.getenv("INKLOOM_DB", "inkloom.db")
    return f"sqlite:///{db_path}"


def get_engine():
    url = get_database_url()
    if url not in _engines:
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engines[url] = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
    return _engines[url]


def get_session():
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return SessionLocal()


def hash_password(password: str) -> str:
    salt = os.getenv("JWT_SECRET", "inkloom-round3-salt-2026")
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


def _seed_defaults(session) -> None:
    if session.query(UserAccount).count() == 0:
        demo_users = [
            ("creator@inkloom.demo", "Casey Creator", "creator", "demo123"),
            ("manager@inkloom.demo", "Morgan Manager", "manager", "demo123"),
            ("reviewer@inkloom.demo", "Riley Reviewer", "reviewer", "demo123"),
        ]
        for email, name, role, pwd in demo_users:
            session.add(UserAccount(email=email, name=name, role=role, password_hash=hash_password(pwd)))

    if session.query(GuidelinePack).count() == 0 and DEFAULT_PACK_PATH.exists():
        raw = json.loads(DEFAULT_PACK_PATH.read_text(encoding="utf-8"))
        session.add(
            GuidelinePack(
                brand=raw.get("brand", "Acme Wellness"),
                version=raw.get("version", "1.0"),
                date=raw.get("date", "2026-11-15"),
                pack_json=json.dumps(raw),
                is_active=1,
                updated_by="system_seed",
            )
        )
    session.commit()


def init_db() -> None:
    eng = get_engine()
    Base.metadata.create_all(bind=eng)
    session = get_session()
    try:
        _seed_defaults(session)
    finally:
        session.close()


def get_active_brand_pack() -> dict:
    try:
        init_db()
        session = get_session()
        try:
            row = (
                session.query(GuidelinePack)
                .filter(GuidelinePack.is_active == 1)
                .order_by(GuidelinePack.id.desc())
                .first()
            )
            if row:
                data = json.loads(row.pack_json)
                data["_db_id"] = row.id
                data["version"] = row.version
                data["date"] = row.date
                data["brand"] = row.brand
                return data
        finally:
            session.close()
    except Exception:
        pass
    if DEFAULT_PACK_PATH.exists():
        return json.loads(DEFAULT_PACK_PATH.read_text(encoding="utf-8"))
    return {"brand": "Acme Wellness", "version": "1.0", "date": "2026-11-15", "terminology": {"preferred": {}, "avoid": []}, "guidelines": [], "facts": []}


def db_backend_info() -> dict:
    url = get_database_url()
    kind = "postgresql" if url.startswith("postgresql") else "sqlite"
    return {"backend": kind, "persistent_cloud": kind == "postgresql"}
