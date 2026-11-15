"""
JWT Authentication & Role Resolution. Owner: Aarush CU
Supports email/password login, registration, and 1-click demo login backed by database users.
"""
import base64
import hashlib
import hmac
import json
import os
import time
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from database import UserAccount, get_session, hash_password, init_db

router = APIRouter()

ROLES = {"creator", "manager", "reviewer"}
JWT_SECRET = os.getenv("JWT_SECRET", "inkloom-round3-jwt-secret-2026")
TOKEN_TTL_SECONDS = 60 * 60 * 24  # 24 hours


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def create_jwt(payload: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    body = {**payload, "iat": int(time.time()), "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    h_enc = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    b_enc = _b64url_encode(json.dumps(body, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{h_enc}.{b_enc}".encode("ascii")
    sig = hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{h_enc}.{b_enc}.{_b64url_encode(sig)}"


def decode_jwt(token: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token structure")
        h_enc, b_enc, s_enc = parts
        signing_input = f"{h_enc}.{b_enc}".encode("ascii")
        expected_sig = hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(_b64url_encode(expected_sig), s_enc):
            raise ValueError("Invalid signature")
        payload = json.loads(_b64url_decode(b_enc).decode("utf-8"))
        if payload.get("exp", 0) < int(time.time()):
            raise ValueError("Token expired")
        return payload
    except Exception as e:
        raise HTTPException(401, f"Invalid or expired session token: {e}")


def resolve_role(authorization: Optional[str] = None, fallback_role: Optional[str] = None) -> str:
    """Resolve authenticated role from Bearer JWT if provided; otherwise fallback for legacy/test callers."""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        payload = decode_jwt(token)
        role = payload.get("role", "")
        if role not in ROLES:
            raise HTTPException(403, f"Invalid role in token: {role}")
        return role
    if fallback_role is not None:
        if fallback_role not in ROLES:
            raise HTTPException(400, f"unknown role '{fallback_role}'")
        return fallback_role
    return "creator"


class LoginRequest(BaseModel):
    email: str
    password: str


class DemoLoginRequest(BaseModel):
    role: str
    name: Optional[str] = None


class RegisterRequest(BaseModel):
    email: str
    name: str
    password: str
    role: str = "creator"


@router.post("/login")
def login(req: LoginRequest) -> dict:
    init_db()
    email = req.email.strip().lower()
    if not email or not req.password:
        raise HTTPException(422, "Email and password are required.")
    session = get_session()
    try:
        user = session.query(UserAccount).filter(UserAccount.email == email).first()
        if not user or user.password_hash != hash_password(req.password):
            raise HTTPException(401, "Invalid email or password.")
        token = create_jwt({"sub": user.email, "name": user.name, "role": user.role, "uid": user.id})
        return {
            "token": token,
            "user": {"id": user.id, "email": user.email, "name": user.name, "role": user.role},
        }
    finally:
        session.close()


@router.post("/register")
def register(req: RegisterRequest) -> dict:
    init_db()
    email = req.email.strip().lower()
    name = req.name.strip()[:60]
    role = req.role.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(422, "Valid email is required.")
    if not name:
        raise HTTPException(422, "Name is required.")
    if len(req.password) < 4:
        raise HTTPException(422, "Password must be at least 4 characters.")
    if role not in ROLES:
        raise HTTPException(400, f"Role must be one of {sorted(ROLES)}")
    session = get_session()
    try:
        if session.query(UserAccount).filter(UserAccount.email == email).first():
            raise HTTPException(409, "An account with this email already exists.")
        user = UserAccount(email=email, name=name, role=role, password_hash=hash_password(req.password))
        session.add(user)
        session.commit()
        session.refresh(user)
        token = create_jwt({"sub": user.email, "name": user.name, "role": user.role, "uid": user.id})
        return {
            "token": token,
            "user": {"id": user.id, "email": user.email, "name": user.name, "role": user.role},
        }
    finally:
        session.close()


@router.post("/demo")
def demo_login(req: DemoLoginRequest) -> dict:
    init_db()
    role = req.role.strip().lower()
    if role not in ROLES:
        raise HTTPException(400, f"unknown role '{role}'")
    session = get_session()
    try:
        demo_email = f"{role}@inkloom.demo"
        user = session.query(UserAccount).filter(UserAccount.email == demo_email).first()
        display_name = (req.name or "").strip()[:60] or (user.name if user else f"Demo {role.title()}")
        uid = user.id if user else 0
        token = create_jwt({"sub": demo_email, "name": display_name, "role": role, "uid": uid})
        return {
            "token": token,
            "user": {"id": uid, "email": demo_email, "name": display_name, "role": role},
        }
    finally:
        session.close()


@router.get("/me")
def me(authorization: Optional[str] = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing Bearer token")
    payload = decode_jwt(authorization.split(" ", 1)[1].strip())
    return {"user": {"email": payload.get("sub"), "name": payload.get("name"), "role": payload.get("role")}}
