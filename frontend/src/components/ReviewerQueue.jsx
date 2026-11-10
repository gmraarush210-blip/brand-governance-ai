import { useEffect, useState } from "react";
import { get } from "../api.js";

export default function ReviewerQueue({ role, onOpen }) {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    get(`/api/approvals/queue?role=${role}`)
      .then((d) => { setItems(d.items || []); setError(""); })
      .catch((e) => { setItems([]); setError(String(e.message || e)); });
  }, [role]);

  return (
    <section>
      <h2>Review queue ({role})</h2>
      <p>{role === "creator" ? "All open findings." : "Open high-risk findings awaiting an authorised reviewer."}</p>
      {error && <p role="alert" style={{ color: "crimson" }}>{error}</p>}
      {items.length === 0 && !error && <p>Nothing waiting.</p>}
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
