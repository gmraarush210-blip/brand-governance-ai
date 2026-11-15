import { useEffect, useState } from "react";
import UploadScreen from "./components/UploadScreen.jsx";
import FindingsView from "./components/FindingsView.jsx";
import ReviewerQueue from "./components/ReviewerQueue.jsx";
import InsightsDashboard from "./components/InsightsDashboard.jsx";
import LoginScreen from "./components/LoginScreen.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import { clearSession, loadNav, loadSession, saveNav, saveSession } from "./auth.js";

const TABS = ["Upload", "Findings", "Review Queue", "Insights"];

export default function App() {
  const [session, setSession] = useState(loadSession);
  const nav = loadNav();
  const [tab, setTab] = useState(TABS.includes(nav.tab) ? nav.tab : "Upload");
  const [submissionId, setSubmissionId] = useState(Number.isInteger(nav.submissionId) ? nav.submissionId : null);

  // Survive page refresh: remember tab + open submission for this browser tab.
  useEffect(() => { saveNav({ tab, submissionId }); }, [tab, submissionId]);

  function login(s) { saveSession(s); setSession(s); }
  function logout() { clearSession(); setSession(null); setTab("Upload"); setSubmissionId(null); }

  if (!session) return <LoginScreen onLogin={login} />;
  const { role, name } = session;

  return (
    <div className="app">
      <div role="note" className="notice">
        <strong>AI-use disclosure:</strong> findings come from rule checks over fictional brand data
        (optionally model-assisted). Suggestions are optional; humans make every approval. Not legal,
        factual or accessibility certification.
      </div>
      <h1>Inkloom Engine</h1>
      <div className="topbar">
        <nav aria-label="Main">
          {TABS.map((t) => (
            <button key={t} onClick={() => setTab(t)} aria-current={tab === t ? "page" : undefined}
              style={{ fontWeight: tab === t ? 700 : 400 }}>{t}</button>
          ))}
        </nav>
        <span className="spacer" />
        <span className={`badge ${role}`} data-testid="who">{name} · {role}</span>
        <button onClick={logout}>Switch role / sign out</button>
      </div>
      <ErrorBoundary resetKey={`${tab}:${submissionId}`}>
        {tab === "Upload" && <UploadScreen onDone={(id) => { setSubmissionId(id); setTab("Findings"); }} />}
        {tab === "Findings" && <FindingsView submissionId={submissionId} role={role}
          onMissing={() => { setSubmissionId(null); setTab("Upload"); }} />}
        {tab === "Review Queue" && <ReviewerQueue role={role} onOpen={(id) => { setSubmissionId(id); setTab("Findings"); }} />}
        {tab === "Insights" && <InsightsDashboard />}
      </ErrorBoundary>
    </div>
  );
}
