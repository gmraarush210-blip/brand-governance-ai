# Responsible Design: Privacy, Security, Human Oversight

| Concern | Safeguard (implemented / planned) |
|---|---|
| PII | Emails/phones are detected and **masked** in findings (`[EMAIL]`, `[PHONE]`); raw values are not echoed. (implemented, tested) |
| Confidential material | Prototype uses synthetic data only. Real pilots need least-privilege access, encrypted transport/storage, defined retention/deletion. (planned) |
| External AI services | None required. If one is added: disclose provider/model, data sent, retention; send only masked, necessary excerpts; keep the rule path as fallback. No training on customer content. |
| Prompt injection | Draft text is treated as data. Rules never execute instructions found in text (see `test_injection_text_is_just_data`). Any future LLM call must confine drafts to a delimited block. |
| False positives / misses | Every finding shows evidence and an uncertainty label; users can reject with a reason; rejection patterns surface in Insights. Not legal, factual or accessibility certification. |
| Human authority | No silent rewriting, auto-approval or auto-publishing. Originals kept as revisions; all decisions attributed by role and timestamped. |
| Bias / fairness | No demographic inference; insights are descriptive and never rank employees. |
| Accessibility | Keyboard-operable controls, labelled inputs, `role="alert"` errors; text/alt-text checks in the engine. |
| Secrets | API keys only via environment variables (`.env`, git-ignored). |

Known limitation: prototype roles are selected in the UI and trusted by the API; production needs real authentication.
