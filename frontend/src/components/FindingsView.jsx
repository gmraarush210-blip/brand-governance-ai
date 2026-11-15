import { useCallback, useEffect, useRef, useState } from "react";
import { get, postForm, postJson } from "../api.js";

const COLORS = { critical: "#b00020", high: "#c62828", medium: "#b26a00", low: "#555", info: "#555" };

export default function FindingsView({ submissionId, role, onMissing }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [missing, setMissing] = useState(false);
  const inFlight = useRef(false);

  const load = useCallback(async (resetDraft = true) => {
    if (!submissionId) return;
    try {
      const d = await get(`/api/submissions/${submissionId}`);
      setData(d); setMissing(false);
      if (resetDraft) setDraft(d.revisions[d.revisions.length - 1].content);
    } catch (e) {
      const msg = String(e.message || e);
      if (/not found/i.test(msg)) setMissing(true);   // e.g. database was reset, or stale id after refresh
      setError(msg);
    }
  }, [submissionId]);

  // Switching submissions must not show the previous one's data or error.
  useEffect(() => { setData(null); setError(""); setMissing(false); load(true); }, [load]);

  // Serialises every write so double-clicks cannot fire duplicate requests.
  async function guarded(fn) {
    if (inFlight.current) return;
    inFlight.current = true; setBusy(true); setError("");
    try { await fn(); } catch (e) { setError(String(e.message || e)); }
    finally { inFlight.current = false; setBusy(false); }
  }

  function act(id, state) {
    let reason = "";
    if (state === "rejected") {
      const r = window.prompt("Reason for rejecting (optional). Cancel to keep the finding open.");
      if (r === null) return;                          // Cancel must not reject
      reason = r;
    }
    return guarded(async () => { await postJson(`/api/approvals/findings/${id}`, { state, role, reason }); await load(false); });
  }

  function decide(decision) {
    const note = window.prompt("Note (optional). Cancel to abort.");
    if (note === null) return;                         // Cancel must not record a decision
    return guarded(async () => {
      await postJson(`/api/approvals/submissions/${submissionId}/decision`, { decision, role, note });
      await load(false);
    });
  }

  function revise() {
    return guarded(async () => {
      await postForm(`/api/submissions/${submissionId}/revise`, { content: draft, note: "creator edit" });
      await postForm(`/api/submissions/${submissionId}/review`, {});
      await load();
    });
  }

  if (!submissionId) return <p>No submission yet. Upload a draft first.</p>;
  if (missing) return (
    <div role="alert" className="card">
      <p className="error">Submission #{submissionId} no longer exists on the server.</p>
      <button onClick={onMissing}>Back to Upload</button>
    </div>
  );
  if (!data) return error ? <p role="alert" className="error">{error}</p> : <p role="status">Loading...</p>;

  const { submission, findings, revisions, decisions, comments } = data;
  const canDecide = role !== "creator";
  const latest = revisions[revisions.length - 1].content;
  const draftBlank = !draft.trim();
  const draftUnchanged = draft === latest;

  return (
    <section>
      <h2>{submission.title} <small>(status: {submission.status}, revision {revisions.length})</small></h2>
      {error && <p role="alert" className="error">{error}</p>}
      <div className="findings-grid">
        <div>
          <h3>Draft (editable → new revision)</h3>
          <textarea aria-label="Draft text" value={draft} onChange={(e) => setDraft(e.target.value)} rows={14} style={{ width: "100%", padding: 8 }} />
          <button onClick={revise} disabled={busy || draftBlank || draftUnchanged}>Save as new revision &amp; re-review</button>
          {draftBlank && <small role="alert" className="error"> Draft cannot be empty.</small>}
          {!draftBlank && draftUnchanged && <small className="muted"> No changes to save.</small>}
          <p style={{ color: "#555" }}>Original text is always preserved in revision history.</p>
        </div>
        <div>
          <h3>Findings ({findings.length})</h3>
          {findings.length === 0 && <p>No issues found by the current rules.</p>}
          {findings.map((f) => (
            <article key={f.id} style={{ border: "1px solid #ddd", borderRadius: 8, padding: 12, marginBottom: 10 }}>
              <strong style={{ color: COLORS[f.severity] }}>[{f.severity.toUpperCase()}]</strong> {f.issue_type}
              {" "}<em>({f.state})</em>
              {f.excerpt && <blockquote style={{ margin: "6px 0", color: "#444" }}>{f.excerpt}</blockquote>}
              <p>{f.explanation}</p>
              <p style={{ color: "#555" }}><em>Source:</em> {f.cited_source}</p>
              {f.suggested_fix && <p style={{ color: "#1b6e3a" }}><em>Suggested fix (optional):</em> {f.suggested_fix}</p>}
              <p style={{ color: "#555" }}><em>{f.uncertainty}</em></p>
              <button disabled={busy || f.state === "accepted"} onClick={() => act(f.id, "accepted")}>Accept</button>{" "}
              <button disabled={busy || f.state === "rejected"} onClick={() => act(f.id, "rejected")}>Reject</button>
            </article>
          ))}
        </div>
      </div>

      {canDecide && (
        <p>
          <strong>Decision ({role}):</strong>{" "}
          <button disabled={busy} onClick={() => decide("approve")}>Approve</button>{" "}
          <button disabled={busy} onClick={() => decide("request_changes")}>Request changes</button>{" "}
          <button disabled={busy} onClick={() => decide("escalate")}>Escalate</button>
        </p>
      )}

      <h3>Audit trail</h3>
      <ul>
        {revisions.map((r) => <li key={`r${r.id}`}>Revision {r.version}: {r.note} ({r.created_at})</li>)}
        {comments.map((c) => <li key={`c${c.id}`}>Comment by {c.author_role}: {c.body}</li>)}
        {decisions.map((d) => <li key={`d${d.id}`}>Decision by {d.role}: <strong>{d.decision}</strong> {d.note}</li>)}
      </ul>
    </section>
  );
}
