"""
Dynamic Brand Guideline Manager & Upload API. Owner: Aarush CU
Supports listing active/historical versions, adding/editing guidelines, prohibited terms,
approved facts, uploading a JSON brand pack, and rolling back/activating versions.
"""
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, File, Header, HTTPException, UploadFile
from pydantic import BaseModel

from database import GuidelinePack, get_active_brand_pack, get_session, init_db
from routes.auth import resolve_role

router = APIRouter()


class GuidelineRuleInput(BaseModel):
    id: str
    section: str
    text: str


class FactInput(BaseModel):
    claim: str
    value: str
    expires_at: Optional[str] = None


class GuidelineUpdatePayload(BaseModel):
    brand: Optional[str] = None
    version: Optional[str] = None
    terminology_avoid: Optional[list[str]] = None
    terminology_preferred: Optional[dict[str, str]] = None
    guidelines: Optional[list[GuidelineRuleInput]] = None
    facts: Optional[list[FactInput]] = None
    role: Optional[str] = None


def _next_version(current_ver: str) -> str:
    parts = current_ver.lstrip("v").split(".")
    try:
        if len(parts) >= 2:
            return f"{parts[0]}.{int(parts[1]) + 1}"
        return f"{int(parts[0]) + 1}.0"
    except ValueError:
        return f"{current_ver}.1"


@router.get("")
def get_guidelines() -> dict:
    pack = get_active_brand_pack()
    session = get_session()
    try:
        versions = [
            {
                "id": r.id,
                "brand": r.brand,
                "version": r.version,
                "date": r.date,
                "is_active": bool(r.is_active),
                "updated_by": r.updated_by,
                "created_at": r.created_at,
            }
            for r in session.query(GuidelinePack).order_by(GuidelinePack.id.desc()).all()
        ]
    finally:
        session.close()
    return {"active": pack, "versions": versions}


@router.post("")
def update_guidelines(
    payload: GuidelineUpdatePayload,
    authorization: Optional[str] = Header(default=None),
) -> dict:
    role = resolve_role(authorization, payload.role or "manager")
    if role not in {"manager", "reviewer"}:
        raise HTTPException(403, "Only managers or reviewers can modify brand guidelines.")

    init_db()
    current = get_active_brand_pack()
    new_pack = json.loads(json.dumps(current))
    new_pack.pop("_db_id", None)

    if payload.brand and payload.brand.strip():
        new_pack["brand"] = payload.brand.strip()[:120]
    new_pack["version"] = (payload.version or "").strip() or _next_version(str(current.get("version", "1.0")))
    new_pack["date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if payload.terminology_avoid is not None:
        clean_avoid = [t.strip() for t in payload.terminology_avoid if t and t.strip()]
        new_pack.setdefault("terminology", {})["avoid"] = clean_avoid

    if payload.terminology_preferred is not None:
        clean_pref = {k.strip().lower(): v.strip() for k, v in payload.terminology_preferred.items() if k.strip() and v.strip()}
        new_pack.setdefault("terminology", {})["preferred"] = clean_pref

    if payload.guidelines is not None:
        new_pack["guidelines"] = [
            {"id": g.id.strip(), "section": g.section.strip(), "text": g.text.strip()}
            for g in payload.guidelines
            if g.id.strip() and g.section.strip() and g.text.strip()
        ]

    if payload.facts is not None:
        new_pack["facts"] = [
            {"claim": f.claim.strip().lower(), "value": f.value.strip(), "expires_at": f.expires_at}
            for f in payload.facts
            if f.claim.strip() and f.value.strip()
        ]

    session = get_session()
    try:
        session.query(GuidelinePack).update({"is_active": 0})
        row = GuidelinePack(
            brand=new_pack["brand"],
            version=new_pack["version"],
            date=new_pack["date"],
            pack_json=json.dumps(new_pack),
            is_active=1,
            updated_by=role,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return {"id": row.id, "version": row.version, "active": get_active_brand_pack()}
    finally:
        session.close()


@router.post("/upload")
async def upload_brand_pack(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None),
) -> dict:
    role = resolve_role(authorization, "manager")
    if role not in {"manager", "reviewer"}:
        raise HTTPException(403, "Only managers or reviewers can upload brand packs.")

    raw_bytes = await file.read(1024 * 1024 + 1)
    if len(raw_bytes) > 1024 * 1024:
        raise HTTPException(413, "Brand pack JSON must be under 1 MB.")
    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except Exception as e:
        raise HTTPException(422, f"Invalid JSON brand pack: {e}")

    if not isinstance(data, dict) or "guidelines" not in data or "terminology" not in data:
        raise HTTPException(422, "Brand pack JSON must contain 'guidelines' and 'terminology' keys.")

    init_db()
    current = get_active_brand_pack()
    brand = str(data.get("brand") or current.get("brand", "Acme Wellness"))[:120]
    version = str(data.get("version") or _next_version(str(current.get("version", "1.0"))))[:32]
    date_str = str(data.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d"))[:32]
    data["brand"] = brand
    data["version"] = version
    data["date"] = date_str

    session = get_session()
    try:
        session.query(GuidelinePack).update({"is_active": 0})
        row = GuidelinePack(
            brand=brand,
            version=version,
            date=date_str,
            pack_json=json.dumps(data),
            is_active=1,
            updated_by=role,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return {"id": row.id, "version": row.version, "active": get_active_brand_pack()}
    finally:
        session.close()


@router.post("/{pack_id}/activate")
def activate_version(pack_id: int, authorization: Optional[str] = Header(default=None)) -> dict:
    role = resolve_role(authorization, "manager")
    if role not in {"manager", "reviewer"}:
        raise HTTPException(403, "Only managers or reviewers can switch active guideline versions.")
    session = get_session()
    try:
        target = session.query(GuidelinePack).filter(GuidelinePack.id == pack_id).first()
        if not target:
            raise HTTPException(404, "Guideline pack version not found.")
        session.query(GuidelinePack).update({"is_active": 0})
        target.is_active = 1
        session.commit()
        return {"id": target.id, "version": target.version, "active": get_active_brand_pack()}
    finally:
        session.close()
