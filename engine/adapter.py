"""
Single entry point used by the API. Owner: M Tejas Navada / Aarush CU

INKLOOM_ENGINE=builtin  -> always use engine/checker.py (rules only)
INKLOOM_ENGINE=auto     -> use the `inkloom_engine` package; if it is missing or fails, fall back to the
                           built-in checker AND say so in result["warnings"] (never silently).
INKLOOM_ENGINE=external -> use `inkloom_engine` only; errors propagate.

`inkloom_engine` calls a language model only if ANTHROPIC_API_KEY is set (see docs/ai_disclosure.md).
"""
import os

from .checker import check
from .formatter import format_result


def run_review(text: str) -> dict:
    mode = os.getenv("INKLOOM_ENGINE", "auto")
    if mode != "builtin":
        try:
            from inkloom_engine.bridge import review_for_api
            return format_result(review_for_api(text), engine="inkloom_engine")
        except ImportError as e:
            if mode == "external":
                raise
            reason = f"inkloom_engine not available ({e})"
        except Exception as e:
            if mode == "external":
                raise
            reason = f"inkloom_engine failed ({type(e).__name__})"
        result = check(text)
        result["warnings"] = [f"{reason}; the built-in rule checker was used instead."]
        return result
    return check(text)
