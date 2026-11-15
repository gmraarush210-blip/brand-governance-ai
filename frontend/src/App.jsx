import { useEffect, useState } from "react";
import brandPack from "../../data/fictional_brand_pack.json";
import UploadScreen from "./components/UploadScreen.jsx";
import FindingsView from "./components/FindingsView.jsx";
import ReviewerQueue from "./components/ReviewerQueue.jsx";
import InsightsDashboard from "./components/InsightsDashboard.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import { ROLES, loadNav, loadSession, saveNav, saveSession } from "./auth.js";

const TABS = ["Upload", "Review queue", "Insights", "Guidelines"];
const ROLE_NAMES = { creator: "Priya Nair", manager: "Morgan Lee", reviewer: "Jordan Blake" };
const STEPS = [
  ["Submit", "Paste copy or attach a PDF."],
  ["Triage findings", "Accept, reject or edit each suggestion."],
  ["Human review", "A reviewer approves, requests changes or escalates."],
  ["Insights", "Track recurring issues across your brand."],
];

export default function App() {
  const [session, setSession] = useState(loadSession);
  const nav = loadNav();
  const [tab, setTab] = useState(TABS.includes(nav.tab) ? nav.tab : "Upload");
  const [submissionId, setSubmissionId] = useState(Number.isInteger(nav.submissionId) ? nav.submissionId : null);
  const [showDisclosure, setShowDisclosure] = useState(true);
  const [showDisclosureDetails, setShowDisclosureDetails] = useState(false);

  useEffect(() => { saveNav({ tab, submissionId }); }, [tab, submissionId]);

  function changeRole(role) {
    const nextSession = { name: ROLE_NAMES[role], role };
    saveSession(nextSession);
    setSession(nextSession);
  }

  function startNewSubmission() {
    setSubmissionId(null);
    setTab("Upload");
  }

  const { role } = session;

  return (
    <div className="app-shell">
      <header className="site-header">
        <a className="brand" href="#main-content" aria-label="Inkloom AI home">
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none"><path d="M12 20h9M16.5 3.5a2.12 2.12 0 0 1 3 3L9 17l-4 1 1-4Z" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </span>
          <span className="brand-copy"><strong>Inkloom AI</strong><small>Brand governance, before publish</small></span>
        </a>
        <nav className="primary-nav" aria-label="Primary">
          {TABS.map((item) => (
            <button className={tab === item ? "nav-link active" : "nav-link"} key={item}
              onClick={() => setTab(item)} aria-current={tab === item ? "page" : undefined}>
              <TabIcon name={item} />{item}
            </button>
          ))}
        </nav>
        <div className="header-actions">
          <label htmlFor="role-select">Acting as</label>
          <select id="role-select" className="role-select" value={role} onChange={(event) => changeRole(event.target.value)} aria-label="Switch demo role">
            {ROLES.map((item) => <option key={item} value={item}>{ROLE_NAMES[item]} · {capitalize(item)}</option>)}
          </select>
          <button className="icon-button" type="button" onClick={startNewSubmission} aria-label="Start a new submission" title="Start a new submission">
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M3 12a9 9 0 1 0 2.64-6.36L3 8m0-5v5h5M12 7v5l3 2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </button>
        </div>
      </header>

      {showDisclosure && <section className="ai-notice" aria-label="AI use disclosure">
        <span className="notice-icon" aria-hidden="true">i</span>
        <div className="notice-copy">
          <p><strong>AI assistance notice:</strong> Inkloom checks copy against sample brand guidelines. Suggestions are never applied automatically, nothing is auto-approved or published, and a human reviewer makes every final decision. <strong>This prototype uses rule-based checks, not AI verification.</strong></p>
          <button className="text-button" type="button" onClick={() => setShowDisclosureDetails((value) => !value)} aria-expanded={showDisclosureDetails}>How we use AI &amp; your data</button>
          {showDisclosureDetails && <p className="notice-detail">Submitted text is reviewed by the configured rule engine. This demo uses fictional Acme Wellness guidance; do not submit confidential or personal information.</p>}
        </div>
        <button className="dismiss-button" type="button" onClick={() => setShowDisclosure(false)} aria-label="Dismiss AI use disclosure">×</button>
      </section>}

      <main id="main-content">
        {tab === "Upload" && <section className="hero-section">
          <div className="hero-inner">
            <p className="hero-eyebrow"><span aria-hidden="true">✦</span> Rule-based review, human-approved</p>
            <h1>Catch brand issues before your<br className="desktop-break" /> content goes live.</h1>
            <p className="hero-description">Submit marketing copy or a PDF. Inkloom flags guideline conflicts with cited sources — your reviewers make the call.</p>
          </div>
        </section>}

        <div className={tab === "Upload" ? "page-content upload-layout" : "page-content inner-page"}>
          <ErrorBoundary resetKey={`${tab}:${submissionId}`}>
            {tab === "Upload" && <>
              <UploadScreen onDone={(id) => { setSubmissionId(id); setTab("Findings"); }} />
              <aside className="workflow-sidebar" aria-label="How review works">
                <section className="surface-card workflow-card">
                  <h2>How it works</h2>
                  <ol className="steps-list">{STEPS.map(([title, description], index) => <li key={title}>
                    <span className="step-number">{index + 1}</span><div><strong>{title}</strong><p>{description}</p></div>
                  </li>)}</ol>
                </section>
                <section className="surface-card scope-card">
                  <h2><span aria-hidden="true">♧</span> MVP scope</h2>
                  <ul><li>Text and PDF review only</li><li>No automatic approval or publishing</li><li>Original content is never altered</li></ul>
                </section>
              </aside>
            </>}
            {tab === "Findings" && <FindingsView submissionId={submissionId} role={role}
              onMissing={() => { setSubmissionId(null); setTab("Upload"); }} />}
            {tab === "Review queue" && <ReviewerQueue role={role} onOpen={(id) => { setSubmissionId(id); setTab("Findings"); }} />}
            {tab === "Insights" && <InsightsDashboard />}
            {tab === "Guidelines" && <Guidelines />}
          </ErrorBoundary>
        </div>
      </main>
      <footer className="site-footer">Inkloom AI · Frontend MVP · Text &amp; PDF only · Human reviewers retain final authority</footer>
    </div>
  );
}

function TabIcon({ name }) {
  const icons = {
    Upload: <><path d="M12 16V4m0 0L7 9m5-5 5 5" /><path d="M20 16.5v2A1.5 1.5 0 0 1 18.5 20h-13A1.5 1.5 0 0 1 4 18.5v-2" /></>,
    "Review queue": <><path d="m4 7 2 2 4-4" /><path d="M13 7h7M13 12h7M13 17h7" /><path d="m4 12 2 2 2-2" /></>,
    Insights: <><path d="M4 19V5m0 14h17" /><path d="M8 15v-3m5 3V7m5 8V9" /></>,
    Guidelines: <><path d="M6 4.5A2.5 2.5 0 0 1 8.5 2H20v18H8.5A2.5 2.5 0 0 0 6 22Z" /><path d="M6 4.5V22M10 7h6M10 11h6" /></>,
  };
  return <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{icons[name]}</svg>;
}

function Guidelines() {
  return <section className="guidelines-page">
    <p className="page-kicker">BRAND REFERENCE</p>
    <h1>Guidelines</h1>
    <p className="page-lede">The review engine checks submitted copy against the active sample brand pack.</p>
    <div className="guideline-summary surface-card"><div><span>ACTIVE BRAND</span><strong>{brandPack.brand}</strong></div><div><span>VERSION</span><strong>{brandPack.version}</strong></div><div><span>LAST UPDATED</span><strong>{brandPack.date}</strong></div></div>
    <div className="guideline-list">{brandPack.guidelines.map((guideline) => <article className="surface-card guideline-card" key={guideline.id}>
      <span className="guideline-id">{guideline.id}</span><div><h2>{guideline.section}</h2><p>{guideline.text}</p></div>
    </article>)}</div>
  </section>;
}

function capitalize(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
