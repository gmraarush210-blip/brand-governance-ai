"""Tests for the inkloom_engine bridge and its use through engine.adapter."""
import json
from pathlib import Path

import pytest

from engine.adapter import run_review
from engine.checker import check, load_pack
from inkloom_engine.bridge import review_for_api

SAMPLE = load_pack()["sample_content"]


def kinds(text):
    return {f["issue_type"] for f in review_for_api(text, llm=None)["findings"]}


def test_sample_content_same_issue_types_as_builtin():
    res = review_for_api(SAMPLE, llm=None)
    assert {"terminology", "unsupported_claim", "stale_fact", "pii"} <= {f["issue_type"] for f in res["findings"]}
    assert all(f["cited_source"] and f["severity"] in ("critical", "high", "medium", "low") for f in res["findings"])
    builtin = {f["issue_type"] for f in check(SAMPLE)["findings"]}
    assert builtin <= {f["issue_type"] for f in res["findings"]}


def test_distinct_rules_on_one_sentence_are_all_reported():
    res = review_for_api("ACME cures everything.", llm=None)["findings"]
    assert {f["severity"] for f in res if f["issue_type"] == "terminology"} == {"high", "low"}


def test_clean_text_has_no_findings():
    assert review_for_api("Acme helps you build a calm routine. Founded in 2019.", llm=None)["findings"] == []


def test_pii_never_echoed_anywhere():
    blob = json.dumps(review_for_api("Email sales@acme.io or call 98765 43210 today.", llm=None))
    assert "sales@acme.io" not in blob and "98765" not in blob


def test_dates_and_big_numbers_are_not_pii():
    assert "pii" not in kinds("Prices run 2026-01-15 to 2026-12-31. We saved 1 000 000 000 rupees.")
    assert "pii" not in {f["issue_type"] for f in check("Prices run 2026-01-15 to 2026-12-31.")["findings"]}
    assert "pii" in kinds("Call +44 20 7946 0958.")


def test_stale_fact_cites_value_and_keeps_spacing():
    f = [x for x in review_for_api("Founded in 2015.", llm=None)["findings"] if x["issue_type"] == "stale_fact"][0]
    assert "2019" in f["explanation"] and f["suggested_fix"] == "Founded in 2019."


def test_offsets_point_at_the_sentence():
    text = "Hello there. ACME cures all."
    for f in review_for_api(text, llm=None)["findings"]:
        assert text[f["start"]:f["end"]] == f["excerpt"]


def test_missing_section_means_no_source_found(tmp_path):
    pack = load_pack()
    pack["guidelines"] = [g for g in pack["guidelines"] if g["id"] != "2.2"]
    p = tmp_path / "pack.json"
    p.write_text(json.dumps(pack), encoding="utf-8")
    f = [x for x in review_for_api("It cures all.", p, llm=None)["findings"] if x["issue_type"] == "terminology"][0]
    assert f["cited_source"] == "No source found" and f["uncertainty"] == "No source found"


def test_adapter_uses_engine_and_reports_fallback(monkeypatch):
    monkeypatch.setenv("INKLOOM_ENGINE", "auto")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    res = run_review(SAMPLE)
    assert res["engine"] == "inkloom_engine" and "human reviewer" in res["disclosure"]
    monkeypatch.setattr("inkloom_engine.bridge.review_for_api", lambda t: 1 / 0)
    res = run_review(SAMPLE)
    assert res["engine"] == "builtin" and "failed" in res["warnings"][0]
    monkeypatch.setenv("INKLOOM_ENGINE", "external")
    with pytest.raises(ZeroDivisionError):
        run_review(SAMPLE)
    monkeypatch.setenv("INKLOOM_ENGINE", "builtin")
    assert run_review(SAMPLE)["engine"] == "builtin"


def test_pdf_limits():
    from engine.extractor import ExtractionError, extract_pdf_text
    for bad in (b"", b"junk", b"%PDF-1.4 " + b"x" * (10 * 1024 * 1024 + 1)):
        with pytest.raises(ExtractionError):
            extract_pdf_text(bad)
