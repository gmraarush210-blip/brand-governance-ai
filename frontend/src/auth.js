// Prototype session handling (client-side only).
// The role is a *demo* identity. The backend trusts the role the client sends, so this is
// NOT real authentication. See README "Known limitations".
export const ROLES = ["creator", "manager", "reviewer"];

export const DEMO_USERS = [
  { role: "creator", name: "Casey Creator", blurb: "Submits drafts, resolves low-risk findings" },
  { role: "manager", name: "Morgan Manager", blurb: "Resolves high-risk findings, approves" },
  { role: "reviewer", name: "Riley Reviewer", blurb: "Authorised reviewer: queue + approvals" },
];

const KEY = "inkloom.session.v1";

export function loadSession() {
  try {
    const s = JSON.parse(window.localStorage.getItem(KEY) || "null");
    if (s && typeof s.name === "string" && ROLES.includes(s.role)) return s;
  } catch { /* storage blocked or corrupted: treat as logged out */ }
  return null;
}

export function saveSession(session) {
  try { window.localStorage.setItem(KEY, JSON.stringify(session)); } catch { /* ignore */ }
}

export function clearSession() {
  try { window.localStorage.removeItem(KEY); window.sessionStorage.removeItem("inkloom.nav.v1"); } catch { /* ignore */ }
}

// Where the user was, so a page refresh does not dump them back on "Upload".
const NAV_KEY = "inkloom.nav.v1";
export function loadNav() {
  try { return JSON.parse(window.sessionStorage.getItem(NAV_KEY) || "{}") || {}; } catch { return {}; }
}
export function saveNav(nav) {
  try { window.sessionStorage.setItem(NAV_KEY, JSON.stringify(nav)); } catch { /* ignore */ }
}
