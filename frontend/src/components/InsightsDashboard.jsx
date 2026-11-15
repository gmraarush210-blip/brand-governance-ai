import { useEffect, useState } from "react";
import { get } from "../api.js";

export default function InsightsDashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { get("/api/insights").then(setData).catch((e) => setError(String(e.message || e))); }, []);

  if (error) return <p role="alert" className="error">{error}</p>;
  if (!data) return <p>Loading...</p>;
  return (
    <section className="content-page">
      <p className="page-kicker">TEAM TRENDS</p>
      <h1>Insights</h1>
      <p className="page-lede">Recurring issues and guideline gaps across reviewed content.</p>
      <div className="metric-grid">
        <article className="surface-card metric-card"><span>OPEN FINDINGS</span><strong>{data.unresolved}</strong><small>Awaiting resolution</small></article>
        <article className="surface-card metric-card"><span>WITHOUT A SOURCE</span><strong>{data.findings_without_source}</strong><small>Need a guideline reference</small></article>
        <article className="surface-card metric-card"><span>ISSUE TYPES</span><strong>{data.by_issue_type.length}</strong><small>Found across submissions</small></article>
      </div>
      <div className="insight-columns">
        <section className="surface-card insight-card"><h2>Findings by issue type</h2>
          {data.by_issue_type.length === 0 ? <p className="muted">No reviewed submissions yet.</p> : <ul className="insight-list">{data.by_issue_type.map((item) => <li key={item.issue_type}><span>{item.issue_type.replaceAll("_", " ")}</span><strong>{item.count}</strong></li>)}</ul>}
        </section>
        <section className="surface-card insight-card"><h2>Most-rejected rules</h2><p className="muted">Repeated rejections may signal unclear guidance.</p>
          {data.frequently_rejected_rules.length === 0 ? <p className="empty-inline">None yet</p> : <ul className="insight-list">{data.frequently_rejected_rules.map((item) => <li key={item.cited_source}><span>{item.cited_source}</span><strong>{item.rejections}</strong></li>)}</ul>}
        </section>
      </div>
      <p className="insight-footnote">Descriptive trends only. No employee ranking.</p>
    </section>
  );
}
