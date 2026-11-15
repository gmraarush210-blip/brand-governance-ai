import { useState } from "react";
import { DEMO_USERS, ROLES } from "../auth.js";

export default function LoginScreen({ onLogin }) {
  const [name, setName] = useState("");
  const [role, setRole] = useState("creator");
  const [error, setError] = useState("");

  function submit(e) {
    e.preventDefault();
    const clean = name.trim().replace(/\s+/g, " ");
    if (!clean) { setError("Enter your name to continue."); return; }
    if (clean.length > 60) { setError("Name must be 60 characters or fewer."); return; }
    onLogin({ name: clean, role });
  }

  return (
    <main className="login">
      <h1>Inkloom Engine</h1>
      <p className="muted">Brand governance review. Sign in to continue.</p>

      <section aria-labelledby="demo-h" className="card">
        <h2 id="demo-h">Try a demo role</h2>
        <p className="muted">One click, no typing. Each role sees different actions.</p>
        <div className="demo-grid">
          {DEMO_USERS.map((u) => (
            <button key={u.role} type="button" className="demo-btn" data-testid={`demo-${u.role}`}
              onClick={() => onLogin({ name: u.name, role: u.role })}>
              <strong>Continue as {u.role}</strong>
              <span>{u.blurb}</span>
            </button>
          ))}
        </div>
      </section>

      <form onSubmit={submit} className="card" noValidate aria-labelledby="signin-h">
        <h2 id="signin-h">Or sign in</h2>
        <label>Your name
          <input value={name} maxLength={80} autoComplete="name" aria-invalid={!!error}
            onChange={(e) => { setName(e.target.value); setError(""); }} />
        </label>
        <label>Role
          <select value={role} onChange={(e) => setRole(e.target.value)}>
            {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </label>
        {error && <p role="alert" className="error">{error}</p>}
        <button type="submit" className="primary">Sign in</button>
      </form>

      <p className="muted small">
        Prototype: roles are demo identities with no password. Server-side rules still apply (creators
        cannot resolve high-risk findings or approve), but this is not production authentication.
      </p>
    </main>
  );
}
