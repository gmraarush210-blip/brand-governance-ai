from fastapi.testclient import TestClient
from main import app

SAMPLE = "ACME cures everything. Contact sales@acme.io. Our app is the fastest in the world."


def make(client):
    sid = client.post("/api/submissions", data={"content": SAMPLE, "title": "T"}).json()["id"]
    findings = client.post(f"/api/submissions/{sid}/review").json()["findings"]
    return sid, findings


def test_health_and_full_workflow():
    with TestClient(app) as c:
        assert c.get("/api/health").json()["status"] == "ok"
        sid, findings = make(c)
        assert findings and all("id" in f for f in findings)

        high = next(f for f in findings if f["severity"] == "high")
        # creator cannot resolve a high-risk finding
        r = c.post(f"/api/approvals/findings/{high['id']}", json={"state": "accepted", "role": "creator"})
        assert r.status_code == 403
        # approval blocked while high-risk findings are open
        r = c.post(f"/api/approvals/submissions/{sid}/decision", json={"decision": "approve", "role": "manager"})
        assert r.status_code == 409
        # reviewer resolves everything high-risk, then manager approves
        for f in findings:
            if f["severity"] in ("high", "critical"):
                assert c.post(f"/api/approvals/findings/{f['id']}",
                              json={"state": "accepted", "role": "reviewer", "comment": "ok"}).status_code == 200
        r = c.post(f"/api/approvals/submissions/{sid}/decision",
                   json={"decision": "approve", "role": "manager", "note": "good"})
        assert r.json()["status"] == "approved"
        detail = c.get(f"/api/submissions/{sid}").json()
        assert len(detail["decisions"]) == 1 and detail["comments"]


def test_creator_cannot_approve():
    with TestClient(app) as c:
        sid, _ = make(c)
        r = c.post(f"/api/approvals/submissions/{sid}/decision", json={"decision": "approve", "role": "creator"})
        assert r.status_code == 403


def test_revision_preserves_original():
    with TestClient(app) as c:
        sid, _ = make(c)
        c.post(f"/api/submissions/{sid}/revise", data={"content": "Acme supports calm.", "note": "fixed"})
        d = c.get(f"/api/submissions/{sid}").json()
        assert [r["version"] for r in d["revisions"]] == [1, 2]
        assert d["revisions"][0]["content"] == SAMPLE
        assert c.post(f"/api/submissions/{sid}/review").json()["findings"] == []


def test_missing_and_bad_inputs():
    with TestClient(app) as c:
        assert c.post("/api/submissions/9999/review").status_code == 404
        assert c.post("/api/submissions", data={"content": "  "}).status_code == 422
        r = c.post("/api/submissions/upload-pdf", files={"file": ("x.pdf", b"junk", "application/pdf")})
        assert r.status_code == 422
        assert c.get("/api/approvals/queue?role=bogus").status_code == 400


def test_queue_and_insights():
    with TestClient(app) as c:
        make(c)
        q = c.get("/api/approvals/queue?role=reviewer").json()
        assert all(i["severity"] in ("high", "critical") for i in q["items"])
        assert "by_issue_type" in c.get("/api/insights").json()


# ---- hostile-input regressions (QA pass) ----
def test_revise_rejects_empty_and_missing():
    with TestClient(app) as c:
        sid, _ = make(c)
        assert c.post(f"/api/submissions/{sid}/revise", data={"content": "   "}).status_code == 422
        assert c.post("/api/submissions/9999/revise", data={"content": "x"}).status_code == 404
        assert len(c.get(f"/api/submissions/{sid}").json()["revisions"]) == 1   # nothing was stored


def test_blank_title_becomes_untitled_and_huge_content_rejected():
    with TestClient(app) as c:
        sid = c.post("/api/submissions", data={"content": "Hello.", "title": "   "}).json()["id"]
        assert c.get(f"/api/submissions/{sid}").json()["submission"]["title"] == "Untitled"
        assert c.post("/api/submissions", data={"content": "a" * 200_001}).status_code == 413


def test_upload_rejects_non_pdf_empty_and_oversized():
    with TestClient(app) as c:
        up = lambda b, n="x.pdf": c.post("/api/submissions/upload-pdf", files={"file": (n, b, "application/pdf")})
        assert up(b"").status_code == 422
        assert up(b"hello, I am a text file").status_code == 422
        assert up(b"%PDF-" + b"0" * (10 * 1024 * 1024)).status_code == 413


def test_double_review_does_not_duplicate_findings():
    with TestClient(app) as c:
        sid, first = make(c)
        second = c.post(f"/api/submissions/{sid}/review").json()["findings"]
        assert len(second) == len(first)
