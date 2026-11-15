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
    <section>
      <h2>Review queue ({role})</h2>
      <p>{role === "creator" ? "All open findings." : "Open high-risk findings awaiting an authorised reviewer."}</p>
      {error && <p role="alert" className="error">{error}</p>}
      {loading && <p role="status">Loading...</p>}
      {!loading && items.length === 0 && !error && <p>Nothing waiting.</p>}
      <ul>
        {items.map((it) => (
          <li key={it.id}>
            #{it.id} [{it.severity}] {it.issue_type}{" "}
            <button onClick={() => onOpen(it.submission_id)}>Open submission {it.submission_id}</button>
          </li>
        ))}
      </ul>
    </section>
  );
}
