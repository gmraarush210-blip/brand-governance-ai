import { useCallback, useEffect, useState } from "react";
import { get, postForm, postJson } from "../api.js";

const COLORS = { critical: "#b00020", high: "#c62828", medium: "#b26a00", low: "#555", info: "#555" };

export default function FindingsView({ submissionId, role }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [draft, setDraft] = useState("");

  const load = useCallback(async () => {
    if (!submissionId) return;
    try {
      const d = await get(`/api/submissions/${submissionId}`);
      setData(d);
      setDraft(d.revisions[d.revisions.length - 1].content);
    } catch (e) { setError(String(e.message || e)); }
  }, [submissionId]);

  useEffect(() => { load(); }, [load]);

  async function act(id, state) {
    setError("");
    let reason = "";
    if (state === "rejected") reason = window.prompt("Reason for rejecting (optional)") || "";
    try { await postJson(`/api/approvals/findings/${id}`, { state, role, reason }); await load(); }
    catch (e) { setError(String(e.message || e)); }
  }

  async function decide(decision) {
    setError("");
    const note = window.prompt("Note (optional)") || "";
    try { await postJson(`/api/approvals/submissions/${submissionId}/decision`, { decision, role, note }); await load(); }
    catch (e) { setError(String(e.message || e)); }
  }

  async function revise() {
    setError("");
    try {
      await postForm(`/api/submissions/${submissionId}/revise`, { content: draft, note: "creator edit" });
      await postForm(`/api/submissions/${submissionId}/review`, {});
      await load();
    } catch (e) { setError(String(e.message || e)); }
  }

  if (!submissionId) return <p>No submission yet. Upload a draft first.</p>;
  if (!data) return <p>{error || "Loading..."}</p>;

  const { submission, findings, revisions, decisions, comments } = data;
  const canDecide = role !== "creator";

  return (
    <section>
      <h2>{submission.title} <small>(status: {submission.status}, revision {revisions.length})</small></h2>
      {error && <p role="alert" style={{ color: "crimson" }}>{error}</p>}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div>
          <h3>Draft (editable → new revision)</h3>
          <textarea aria-label="Draft text" value={draft} onChange={(e) => setDraft(e.target.value)} rows={14} style={{ width: "100%", padding: 8 }} />
          <button onClick={revise}>Save as new revision &amp; re-review</button>
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
              <button onClick={() => act(f.id, "accepted")}>Accept</button>{" "}
              <button onClick={() => act(f.id, "rejected")}>Reject</button>
            </article>
          ))}
        </div>
      </div>

      {canDecide && (
        <p>
          <strong>Decision ({role}):</strong>{" "}
          <button onClick={() => decide("approve")}>Approve</button>{" "}
          <button onClick={() => decide("request_changes")}>Request changes</button>{" "}
          <button onClick={() => decide("escalate")}>Escalate</button>
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
