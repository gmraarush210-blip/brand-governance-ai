# Inkloom Engine

Pre-publication brand governance. Inkloom reviews draft text/PDF content against approved
guidelines, facts and terminology, explains every finding with the **cited source passage**
(or an explicit "No source found"), suggests optional fixes, and routes high-risk items to a
human reviewer. Nothing is auto-rewritten, auto-approved or auto-published.

> Prototype status: all data is **fictional** (`data/fictional_brand_pack.json`). See
> `docs/` for the full Round 1 plan, architecture, privacy design, testing log and AI disclosure.

## Team and ownership
| Area | Owner | Key files |
|------|-------|-----------|
| AI review engine | M Tejas Navada | `engine/`, `inkloom_engine/` (if used) |
| Backend and workflow | Aarush C U | `main.py`, `database.py`, `routes/` |
| Frontend and UX | K H Varun | `frontend/src/` |
| Research, data, docs | Karthik R | `docs/`, `data/` |

## Quick start
```bash
# Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
uvicorn main:app --reload           # http://localhost:8000/docs

# Frontend (second terminal)
cd frontend
npm install
npm run dev                         # http://localhost:5173
```

Optionally copy `.env.example` to `.env`. By default `INKLOOM_ENGINE=auto`: if the separate
`inkloom_engine` package is importable it is used, otherwise the built-in rule engine in `engine/`
runs, so the demo always works.

## Demo script (Round 2 target)
1. Open the UI, paste the `sample_content` from `data/fictional_brand_pack.json`, **Submit & review**.
2. See cited findings: prohibited terms, unsupported claim, stale fact (founded year), masked PII.
3. As **creator**, try to accept a High finding: it is refused (needs reviewer/manager).
4. Switch role to **reviewer**, resolve the High findings with a comment.
5. Edit the draft in the left panel, **Save as new revision & re-review**: original is preserved.
6. Switch to **manager**, **Approve**. Open the audit trail (revisions, comments, decisions).
7. Open **Insights** for recurring issue types and most-rejected rules.

## API summary
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/submissions` | create draft (revision 1) |
| POST | `/api/submissions/upload-pdf` | extract text from PDF |
| POST | `/api/submissions/{id}/review` | run engine, store findings |
| POST | `/api/submissions/{id}/revise` | new revision (original kept) |
| GET | `/api/submissions/{id}` | submission, revisions, findings, comments, decisions |
| GET | `/api/approvals/queue?role=` | open findings (high-risk only for manager/reviewer) |
| POST | `/api/approvals/findings/{id}` | accept / reject / comment (role-checked) |
| POST | `/api/approvals/submissions/{id}/decision` | approve / request_changes / escalate |
| GET | `/api/insights` | recurring issues, rejected rules, guideline gaps |

## Tests
```bash
python -m pytest tests -v --cov=engine --cov=routes --cov-branch
```
