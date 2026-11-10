# AI Tools, Libraries and Data Disclosure

## AI assistance used in building
- An AI assistant (Claude, Anthropic) helped generate the repository scaffold, backend routes, rule-based
  checker, frontend components, tests and documentation drafts. All output was reviewed and run by the team.
  > TODO: team edits this list to match exactly what each member used (including any other AI tools).

## AI in the product
- **Always on (no model):** rule checks (avoid-list terms, absolute claims, brand name, personal data,
  accessibility) and comparison against the approved fact sheet, all driven by `data/fictional_brand_pack.json`.
- **Optional language-model step:** runs only if `ANTHROPIC_API_KEY` is set (model: `INKLOOM_LLM_MODEL`,
  default `claude-sonnet-5-5`, via the Anthropic API). **Not set in the demo by default, so nothing leaves the machine.**
  When enabled, the numbered sentences of the draft and the relevant guideline excerpts and approved facts are sent to
  the provider. Before sending, email addresses, phone numbers and ID numbers are masked; names and postal addresses
  are **not** masked.
- **Guardrails on the model:** it refers to sentences by number (so flagged text always comes from the real draft);
  it may cite only sources we supplied and must quote them, and the quote is checked against the stored text. A finding
  that fails the check is shown as "No source found" with severity capped at medium; low-confidence findings are labelled
  "AI uncertain". The draft is passed as data, not instructions. If the model call fails, rule results are still returned
  with a warning.
- Every result carries a `disclosure` line saying whether a model was used, and `engine` says which engine ran
  (`inkloom_engine`, `inkloom_engine+llm` or `builtin`). If the engine package fails, the fallback to the built-in rules is
  reported in `warnings`.
- Findings are suggestions. Nothing is rewritten, approved or published automatically; humans decide.

## Libraries (open source, under their own licences)
FastAPI, Uvicorn, Pydantic, python-multipart, pypdf, pytest, pytest-cov, httpx, React, Vite, @vitejs/plugin-react.

## Data
All demo data is fictional (`data/fictional_brand_pack.json`). No real customer or confidential content used.

## Event rules
Development done within the official build window; earlier work limited to research and planning.
