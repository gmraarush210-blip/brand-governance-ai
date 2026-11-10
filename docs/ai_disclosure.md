# AI Tools, Libraries and Data Disclosure

## AI assistance used in building
- An AI assistant (Claude, Anthropic) helped generate the repository scaffold, backend routes, rule-based
  checker, frontend components, tests and documentation drafts. All output was reviewed and run by the team.
  > TODO: team edits this list to match exactly what each member used (including any other AI tools).

## AI in the product
- The built-in engine is **rule-based** (regex + approved brand data). No model is called by default, and no
  draft text is sent to any external service.
- An optional separate `inkloom_engine` package may be used if present (`INKLOOM_ENGINE=auto`).
  > TODO: Tejas to state whether it calls an LLM, which provider/model, and what data is sent.

## Libraries (open source, under their own licences)
FastAPI, Uvicorn, Pydantic, python-multipart, pypdf, pytest, pytest-cov, httpx, React, Vite, @vitejs/plugin-react.

## Data
All demo data is fictional (`data/fictional_brand_pack.json`). No real customer or confidential content used.

## Event rules
Development done within the official build window; earlier work limited to research and planning.
