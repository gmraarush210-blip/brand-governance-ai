import { useEffect, useState } from "react";
import { get } from "../api.js";

export default function InsightsDashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { get("/api/insights").then(setData).catch((e) => setError(String(e.message || e))); }, []);

  if (error) return <p role="alert" style={{ color: "crimson" }}>{error}</p>;
  if (!data) return <p>Loading...</p>;
  return (
    <section>
      <h2>Recurring issues &amp; guideline gaps</h2>
      <p>Unresolved findings: <strong>{data.unresolved}</strong> · Findings with no source: <strong>{data.findings_without_source}</strong></p>
      <h3>By issue type</h3>
      <ul>{data.by_issue_type.map((s) => <li key={s.issue_type}>{s.issue_type}: <strong>{s.count}</strong></li>)}</ul>
      <h3>Most-rejected rules (possibly unclear guidelines)</h3>
      {data.frequently_rejected_rules.length === 0 ? <p>None yet.</p> :
        <ul>{data.frequently_rejected_rules.map((s) => <li key={s.cited_source}>{s.cited_source}: {s.rejections}</li>)}</ul>}
      <p style={{ color: "#555" }}>Descriptive trends only. No employee ranking.</p>
    </section>
  );
}
