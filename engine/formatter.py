"""
Structured output shaping and validation. Owner: M Tejas Navada
Every finding is validated before it reaches the UI.
"""
SEVERITIES = ("critical", "high", "medium", "low", "info")
FIELDS = ("issue_type", "severity", "excerpt", "explanation", "cited_source", "suggested_fix", "uncertainty")


def to_finding(issue_type="", severity="info", excerpt="", explanation="",
               cited_source="", suggested_fix="", uncertainty="", **_ignored) -> dict:
    if severity not in SEVERITIES:
        severity = "info"
    return {
        "issue_type": issue_type or "unknown",
        "severity": severity,
        "excerpt": excerpt,
        "explanation": explanation,
        "cited_source": cited_source or "No source found",
        "suggested_fix": suggested_fix,
        "uncertainty": uncertainty or ("No source found" if not cited_source else "Source found / rule-based"),
    }


def format_result(raw: dict, engine: str = "builtin") -> dict:
    findings = [to_finding(**f) for f in raw.get("findings", []) if isinstance(f, dict)]
    findings.sort(key=lambda f: SEVERITIES.index(f["severity"]))
    return {"findings": findings, "count": len(findings), "engine": engine}
