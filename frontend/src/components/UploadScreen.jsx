import { useState } from "react";
import { API, postForm } from "../api.js";

export default function UploadScreen({ onDone }) {
  const [content, setContent] = useState("");
  const [title, setTitle] = useState("Untitled");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function onPdf(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`${API}/api/submissions/upload-pdf`, { method: "POST", body: fd });
      if (!res.ok) throw new Error((await res.json()).detail || "PDF extraction failed");
      const data = await res.json();
      setContent(data.text);
      setTitle(data.filename);
    } catch (err) { setError(String(err.message || err)); }
  }

  async function submit() {
    setBusy(true); setError("");
    try {
      const created = await postForm("/api/submissions", { content, title });
      await postForm(`/api/submissions/${created.id}/review`, {});
      onDone(created.id);
    } catch (err) { setError(String(err.message || err)); } finally { setBusy(false); }
  }

  return (
    <section>
      <h2>Submit a draft</h2>
      <label>Title
        <input value={title} onChange={(e) => setTitle(e.target.value)} style={{ display: "block", width: "100%", padding: 8, marginBottom: 8 }} />
      </label>
      <label>Upload a PDF (text-based)
        <input type="file" accept="application/pdf" onChange={onPdf} style={{ display: "block", marginBottom: 8 }} />
      </label>
      <label>Or paste text
        <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={12}
          style={{ display: "block", width: "100%", padding: 8 }} />
      </label>
      <button onClick={submit} disabled={busy || !content.trim()} style={{ marginTop: 8, padding: "8px 16px" }}>
        {busy ? "Reviewing..." : "Submit & review"}
      </button>
      {error && <p role="alert" style={{ color: "crimson" }}>{error}</p>}
    </section>
  );
}
