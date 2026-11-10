# Workflow gaps found in review (routes/ and database.py) — for Aarush

Found by reading the code; the API tests could not be run in the review environment (no FastAPI), so please
confirm each one with a quick test.

1. **Approval can skip the review.** `decide()` only counts open high-risk findings on the latest revision. A draft that
   was never reviewed, or a new revision created by `/revise` that has not been re-reviewed, has zero findings and can be
   approved. Fix: record `reviewed_revision` (or a `reviews` row) when `/review` runs, and in `approve` require
   `reviewed_revision == MAX(version)`; otherwise return 409 "latest revision has not been reviewed".
2. **No status state machine.** An approved submission can be approved/rejected again, and `request_changes` can be issued
   on a draft. Fix: allow `approve/request_changes/escalate` only from `reviewed`/`escalated`; creators resubmit via revise.
3. **Re-running `/review` wipes human decisions.** It deletes all findings for the revision (including accepted/rejected
   ones) and leaves comments pointing at deleted finding ids. Fix: refuse to re-review a revision that already has
   non-open findings (or when status is approved), or keep old findings and mark them `superseded`.
4. **Queue and insights include old revisions.** `/queue` selects open findings of every revision of every submission;
   `/insights` counts all revisions, so "unresolved" is inflated. Fix: join on each submission's latest revision.
5. **Roles are client-asserted** (`role` in the body/query), so a creator can claim to be a reviewer. Fine for a prototype,
   but state it in the plan (auth is out of scope) rather than leaving it to be discovered.
6. **Show the engine's warnings.** In `review_submission`, also return `result.get("warnings")` and
   `result.get("disclosure")` so the UI's disclosure banner can say whether a model was used or a fallback happened.
7. Optional: `result["findings"]` now include `start`/`end` (offsets into the revision text). Add `start_char`/`end_char`
   columns to `findings` if the UI should highlight the exact span.
