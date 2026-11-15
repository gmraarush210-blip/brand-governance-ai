import { useEffect, useState } from "react";
import { get } from "../api.js";

export default function ReviewerQueue({ role, onOpen }) {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;                 // ignore late responses after unmount / role change
    setLoading(true);
    get(`/api/approvals/queue?role=${encodeURIComponent(role)}`)
      .then((d) => { if (!cancelled) { setItems(d.items || []); setError(""); } })
      .catch((e) => { if (!cancelled) { setItems([]); setError(String(e.message || e)); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [role]);

  return (
    <section className="content-page">
      <p className="page-kicker">HUMAN REVIEW</p>
      <h1>Reviewer queue</h1>
      <p className="page-lede">{role === "creator" ? "All open findings." : "Open high-risk findings awaiting an authorised reviewer."}</p>
      {error && <p role="alert" className="error surface-card">{error}</p>}
      {loading && <p role="status" className="surface-card loading-state">Loading review queue…</p>}
      {!loading && items.length === 0 && !error && <div className="surface-card empty-state"><span className="empty-icon" aria-hidden="true">✓</span><h2>Nothing waiting</h2><p>New high-risk findings will appear here for human review.</p></div>}
      {!loading && items.length > 0 && <div className="queue-list">{items.map((it) => (
        <article className="surface-card queue-item" key={it.id}>
          <div><span className={`severity-pill severity-${it.severity}`}>{it.severity}</span><strong>{it.issue_type.replaceAll("_", " ")}</strong><p>Submission #{it.submission_id} · Finding #{it.id}</p></div>
          <button className="secondary-button" onClick={() => onOpen(it.submission_id)}>Review submission <span aria-hidden="true">→</span></button>
        </article>
      ))}</div>}
    </section>
  );
}
