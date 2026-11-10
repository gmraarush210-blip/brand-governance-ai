# Testing and Reliability Log

Run: `python -m pytest tests -v --cov=engine --cov=routes --cov-branch`
Latest result: **12 passed**, ~80% line+branch coverage of `engine/` and `routes/` (extractor/adapter fallbacks least covered).

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
- Frontend automated tests (manual walkthrough only)

## Bug log
| # | Found | Fix | Owner |
|---|---|---|---|
| 1 | Pasted scaffold lost underscores/quotes (`__init__`, `["*"]`, template literals) | Rewritten and verified by running tests/build | Aarush |
| 2 | Findings had no IDs so accept/reject could not persist | Findings now returned from DB with IDs | Aarush |
| 3 | Brand regex matched `acme` inside email domain | Lookarounds exclude `@`, `.` and word chars | Tejas |
