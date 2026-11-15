# Inkloom AI: Brand Governance Review

Checks marketing copy against a codified brand guideline pack, cites the rule behind every finding, and
routes risky findings to a human. **Nothing is ever auto-published**: approval only records a human decision.

Live demo: https://inkloom-ai-eta.vercel.app/ · Repo: https://github.com/gmraarush210-blip/brand-governance-ai

## What it does
- **Submit** pasted text or a text-based PDF. Every edit is saved as a new revision; the original is kept.
- **Review** with a rule engine: prohibited terms, unsupported absolute claims, stale facts, brand-name casing,
  personal data (masked in output) and accessibility. Each finding has severity, excerpt, cited guideline
  (with version and date), suggested fix and an uncertainty label. No evidence means "No source found".
- **Resolve** by role: creators handle low-risk findings; high-risk ones need a manager or reviewer.
  Approval is blocked while any high-risk finding is open.
- **Learn** from the Insights tab: recurring issues, most-rejected rules, findings without a source.

## Quick start (about 3 minutes)
Prerequisites: **Python 3.10+** and **Node 18+**.

```bash
git clone https://github.com/gmraarush210-blip/brand-governance-ai.git
cd brand-governance-ai

# 1. Backend  (terminal 1)
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
INKLOOM_ENGINE=builtin uvicorn main:app --reload --port 8000
#   Windows PowerShell:  $env:INKLOOM_ENGINE="builtin"; uvicorn main:app --reload --port 8000

# 2. Frontend (terminal 2)
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. Check the API at http://localhost:8000/api/health (interactive docs at `/docs`).

> The backend does not read `.env` by itself, so set variables in the shell as shown above.
> `INKLOOM_ENGINE=builtin` uses the bundled rule engine; the default `auto` does the same unless an optional
> external `inkloom_engine` package is installed.

## Try the demo (60 seconds)
1. On the login screen click **Continue as creator**.
2. On **Upload**, paste the sample draft and press **Submit & review**:
   `ACME cures everything and is the fastest in the world. Contact sales@acme.io to guarantee results. Founded in 2015.`
3. Findings appear with cited sources. As creator, try to Accept a High finding: it is refused.
4. Click **Switch role / sign out**, then **Continue as reviewer**. Open **Review Queue**, open the submission,
   resolve the High findings, then **Approve**. Check the audit trail at the bottom.

## Roles
| Role | Can do |
|---|---|
| creator | Submit, edit, resolve low and medium findings |
| manager | Resolve high-risk findings, approve / request changes / escalate |
| reviewer | Same as manager, plus a queue filtered to high-risk findings |

Roles are **demo identities with no password**. The server enforces the role rules, but it trusts the role the
client sends, so this is not production authentication.

## Configuration
| Variable | Default | Purpose |
|---|---|---|
| `INKLOOM_ENGINE` | `auto` | `builtin` forces the bundled rule engine |
| `INKLOOM_DB` | `inkloom.db` | SQLite file path |
| `CORS_ORIGINS` | localhost:5173,3000 | Comma-separated allowed browser origins |
| `VITE_API_URL` (frontend) | `http://localhost:8000` | Where the frontend finds the API |

## Tests
```bash
pip install -r requirements.txt
python -m pytest tests -v
```
Manual hostile-input checklist and the bug log are in [`docs/testing_log.md`](docs/testing_log.md).

## Project layout
```
main.py               FastAPI app (entry point)
routes/               submissions, approvals, insights endpoints
engine/               rule checker, PDF extractor, output formatter, adapter
data/                 fictional brand pack (guidelines + approved facts)
database.py           SQLite schema and connection
frontend/             React + Vite UI (login, upload, findings, queue, insights)
tests/                engine and API tests
docs/                 architecture, privacy, testing log, demo script, AI disclosure
```
`backend/main.py` is an older standalone app that is not used by the steps above.

## Troubleshooting
| Symptom | Fix |
|---|---|
| "Cannot reach the server" in the UI | Backend not running, or `VITE_API_URL` points elsewhere |
| Browser console shows a CORS error | Add your frontend origin to `CORS_ORIGINS` |
| Port 8000 or 5173 busy | Change `--port` / set `VITE_API_URL`; Vite picks the next free port and you must add it to `CORS_ORIGINS` |
| PDF says "no extractable text" | The PDF is scanned images; paste the text instead |
| `ModuleNotFoundError` | Activate the virtualenv and rerun `pip install -r requirements.txt` |

## Known limitations
- Not real authentication (see Roles). Brand data is fictional.
- SQLite does not persist on Vercel serverless; use a hosted database for a real deployment.
- Rule-based checks only: they can miss issues and are not legal, factual or accessibility certification.
