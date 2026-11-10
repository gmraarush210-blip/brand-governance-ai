import { useState } from "react";
import UploadScreen from "./components/UploadScreen.jsx";
import FindingsView from "./components/FindingsView.jsx";
import ReviewerQueue from "./components/ReviewerQueue.jsx";
import InsightsDashboard from "./components/InsightsDashboard.jsx";

const TABS = ["Upload", "Findings", "Review Queue", "Insights"];
const ROLES = ["creator", "manager", "reviewer"];

export default function App() {
  const [tab, setTab] = useState("Upload");
  const [submissionId, setSubmissionId] = useState(null);
  const [role, setRole] = useState("creator");

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: 24, maxWidth: 1100, margin: "0 auto", color: "#111" }}>
      <div role="note" style={{ background: "#eef4ff", border: "1px solid #b6ccff", padding: 10, borderRadius: 8, marginBottom: 16 }}>
        <strong>AI-use disclosure:</strong> findings come from rule checks over fictional brand data
        (optionally model-assisted). Suggestions are optional; humans make every approval. Not legal,
        factual or accessibility certification.
      </div>
      <h1>Inkloom Engine</h1>
      <div style={{ display: "flex", gap: 16, alignItems: "center", marginBottom: 16, flexWrap: "wrap" }}>
        <nav aria-label="Main" style={{ display: "flex", gap: 8 }}>
          {TABS.map((t) => (
            <button key={t} onClick={() => setTab(t)} aria-current={tab === t ? "page" : undefined}
              style={{ padding: "8px 14px", fontWeight: tab === t ? 700 : 400 }}>{t}</button>
          ))}
        </nav>
        <label>Role:{" "}
          <select value={role} onChange={(e) => setRole(e.target.value)}>
            {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </label>
      </div>
      {tab === "Upload" && <UploadScreen onDone={(id) => { setSubmissionId(id); setTab("Findings"); }} />}
      {tab === "Findings" && <FindingsView submissionId={submissionId} role={role} />}
      {tab === "Review Queue" && <ReviewerQueue role={role} onOpen={(id) => { setSubmissionId(id); setTab("Findings"); }} />}
      {tab === "Insights" && <InsightsDashboard />}
    </div>
  );
}
