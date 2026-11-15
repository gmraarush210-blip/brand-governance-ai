# Testing and Reliability Log

Run: `python -m pytest tests -v --cov=engine --cov=routes --cov-branch`
Latest result: engine suite **18 passed** (run). API suite has 9 tests, 4 of them new hostile-input regressions; **not run in the QA environment** (no FastAPI install available), so run `python -m pytest tests -v` before demo day.

## Covered
| Area | Test |
|---|---|
| Cited findings on problematic draft | `test_sample_content_triggers_cited_findings` |
| Clean draft, no false alarm | `test_clean_text_has_no_findings` |
| PII masked | `test_pii_is_masked_in_output` |
| Stale fact vs approved fact | `test_stale_fact_cites_approved_value` |
| Alt-text presence | `test_alt_text_missing` |
| Prompt-injection text treated as data | `test_injection_text_is_just_data` |
| Unreadable PDF | `test_bad_pdf_raises`, `test_missing_and_bad_inputs` |
| Role rules: creator blocked on High, approve blocked while High open | `test_health_and_full_workflow` |
| Creator cannot approve | `test_creator_cannot_approve` |
| Revision keeps original | `test_revision_preserves_original` |
| Queue and insights | `test_queue_and_insights` |

## Not yet tested (honest gaps)
- Empty/scanned PDF with a real file; conflicting guidelines; service timeout (when an LLM is added)
- Usability sessions with target users; tone checks across dialects
- Frontend automated tests (none). The QA-pass frontend fixes below were syntax-checked but **not exercised in a browser**; run the manual checklist before demo day

## Bug log
| # | Found | Fix | Owner |
|---|---|---|---|
| 1 | Pasted scaffold lost underscores/quotes (`__init__`, `["*"]`, template literals) | Rewritten and verified by running tests/build | Aarush |
| 2 | Findings had no IDs so accept/reject could not persist | Findings now returned from DB with IDs | Aarush |
| 3 | Brand regex matched `acme` inside email domain | Lookarounds exclude `@`, `.` and word chars | Tejas |
| 4 | API would not start: `routes/submissions.py` imported `inkloom_engine`, but the package is `engine/` | Import changed to `from engine import ...` | Tejas |
| 5 | **Review hung for minutes on a 200k-digit paste** (unbounded email/phone regex went quadratic) | Bounded quantifiers + lookbehind; regression tests | Tejas |
| 6 | Text full of phone-like numbers produced thousands of findings, each re-scanning the document | Excerpts windowed to 300 chars, 25 findings max per rule | Tejas |
| 7 | `/revise` accepted empty content, creating a blank revision | 422 on empty, 413 over 200k chars | Tejas |
| 8 | Upload: non-PDF/empty/huge files only failed after the round trip; a non-JSON error (413, proxy page) crashed with "Unexpected token"; re-picking the same file after a failure did nothing | Client checks type/size/empty; server checks `%PDF-` header and 10 MB cap; tolerant error parsing; input reset | Tejas |
| 9 | Double-click on Submit, or retry after a failed review, created duplicate submissions | In-flight guard; retry reuses the created submission id | Tejas |
| 10 | Page refresh dropped the user back on Upload with no submission | Tab, open submission and session persisted | Tejas |
| 11 | Cancel on the Reject/decision prompt still performed the action | Cancel now aborts | Tejas |
| 12 | Switching submissions briefly showed the old one; Accept/Reject discarded unsaved draft edits; stale id gave a dead-end spinner | State reset on switch; draft kept; "no longer exists" screen with a way out | Tejas |
| 13 | Backend down showed a bare "Failed to fetch"; a thrown render error white-screened the app | Plain-language message naming the API URL; error boundary | Tejas |
| 14 | Blank title stored as an empty string | Falls back to "Untitled" (client and server) | Tejas |
| 15 | "Save as new revision" allowed with unchanged or empty text | Button disabled with an inline reason | Tejas |

## Hostile-judge manual checklist (run in a browser)
| Try this | Expected |
|---|---|
| Demo role buttons on the login screen | Signed in at once; header shows name and role |
| Refresh on every tab | Stays signed in, same tab and submission |
| Submit with empty or whitespace-only text | Button disabled |
| Double-click Submit & review | One submission only |
| Stop the backend, then submit | "Cannot reach the server at ..."; restart, press Submit again: one submission |
| Upload `.txt`, an empty file, a renamed `.exe`, a >10 MB file | Clear error, nothing submitted |
| Upload a scanned/blank PDF | "no extractable text" |
| Creator tries to accept a High finding | 403 message shown |
| Cancel on Reject / decision prompt | Nothing changes |
| Paste 200k digits | Review returns in well under a second |
| Edit the draft, click Accept on a finding | Draft edits are kept |
| Create a submission, redeploy, then reopen it | Submission remains available from Neon |

## Known limitations
- Roles are not real authentication: the server trusts the role the client sends.
- `backend/main.py` is an unused second app, kept for reference.
- Persistence uses Neon Postgres; configure `DATABASE_URL` in every Vercel project/environment serving the API.
