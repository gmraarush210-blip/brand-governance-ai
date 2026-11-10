"""
Single entry point used by the API. Owner: M Tejas Navada / Aarush CU

INKLOOM_ENGINE=builtin -> always use engine/checker.py
INKLOOM_ENGINE=auto    -> use the external `inkloom_engine` package if installed and working,
                          otherwise fall back to the built-in rule checker (keeps the demo alive).
"""
import json
import os

from .checker import check
from .formatter import format_result


def _normalize(result) -> dict:
    """Accept dict / {'frontend_payload': ...} / JSON string / pydantic object."""
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except ValueError:
            return {"findings": []}
    if hasattr(result, "model_dump"):
        result = result.model_dump()
    elif hasattr(result, "dict") and callable(result.dict):
        result = result.dict()
    if isinstance(result, dict):
        if "findings" not in result and isinstance(result.get("frontend_payload"), dict):
            result = result["frontend_payload"]
        return {"findings": result.get("findings", [])}
    return {"findings": []}


def run_review(text: str) -> dict:
    mode = os.getenv("INKLOOM_ENGINE", "auto")
    if mode != "builtin":
        try:
            from inkloom_engine import review as external_review
            return format_result(_normalize(external_review(text)), engine="inkloom_engine")
        except ImportError:
            pass
        except Exception:
            if mode == "external":
                raise
    return check(text)
