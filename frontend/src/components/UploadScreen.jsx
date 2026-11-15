import { useRef, useState } from "react";
import { postFile, postForm } from "../api.js";

export const MAX_PDF_BYTES = 10 * 1024 * 1024;   // keep in sync with routes/submissions.py
export const MAX_CHARS = 200_000;

export function validatePdf(file) {
  if (!file) return "No file selected.";
  const looksPdf = file.type === "application/pdf" || /\.pdf$/i.test(file.name);
  if (!looksPdf) return `"${file.name}" is not a PDF. Upload a .pdf file or paste the text instead.`;
  if (file.size === 0) return `"${file.name}" is empty.`;
  if (file.size > MAX_PDF_BYTES) return `"${file.name}" is larger than ${MAX_PDF_BYTES / 1024 / 1024} MB.`;
  return "";
}

export default function UploadScreen({ onDone }) {
  const [content, setContent] = useState("");
  const [title, setTitle] = useState("Untitled");
  const [busy, setBusy] = useState(false);
  const [reading, setReading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const inFlight = useRef(false);      // blocks double-click / double-Enter before React re-renders
  const created = useRef(null);        // {id, content, title}: reused so a retry never duplicates the submission
  const pdfSeq = useRef(0);            // ignore stale responses if the user picks another file quickly

  async function onPdf(e) {
    const input = e.target;
    const file = input.files?.[0];
    if (!file) return;                 // user cancelled the picker
    setError(""); setNotice("");
    const problem = validatePdf(file);
    if (problem) { setError(problem); input.value = ""; return; }
    const seq = ++pdfSeq.current;
    setReading(true);
    try {
      const data = await postFile("/api/submissions/upload-pdf", file);
      if (seq !== pdfSeq.current) return;
      setContent(data.text); setTitle(data.filename || file.name);
      setNotice(`Extracted text from ${file.name}. Review it below, then submit.`);
    } catch (err) {
      if (seq === pdfSeq.current) setError(String(err.message || err));
    } finally {
      if (seq === pdfSeq.current) setReading(false);
      input.value = "";                // allows re-selecting the same file after a failure
    }
  }

  async function submit(e) {
    e?.preventDefault();
    if (inFlight.current) return;
    const text = content.trim();
    if (!text) { setError("Paste some text or upload a PDF first."); return; }
    if (text.length > MAX_CHARS) { setError(`Draft is too long (${text.length.toLocaleString()} characters, max ${MAX_CHARS.toLocaleString()}).`); return; }
    const cleanTitle = title.trim() || "Untitled";
    inFlight.current = true; setBusy(true); setError(""); setNotice("");
    try {
      let id = created.current && created.current.content === text && created.current.title === cleanTitle
        ? created.current.id : null;
      if (id === null) {
        const made = await postForm("/api/submissions", { content: text, title: cleanTitle });
        id = made.id;
        created.current = { id, content: text, title: cleanTitle };
      }
      await postForm(`/api/submissions/${id}/review`, {});
      created.current = null;
      onDone(id);
    } catch (err) {
      setError(`${String(err.message || err)} You can press Submit again; it will not create a duplicate.`);
    } finally { inFlight.current = false; setBusy(false); }
  }

  const disabled = busy || reading || !content.trim();
  return (
    <form onSubmit={submit} noValidate>
      <h2>Submit a draft</h2>
      <label>Title
        <input value={title} maxLength={120} onChange={(e) => setTitle(e.target.value)}
          style={{ display: "block", width: "100%", padding: 8, marginBottom: 8 }} />
      </label>
      <label>Upload a PDF (text-based, up to 10 MB)
        <input type="file" accept="application/pdf,.pdf" onChange={onPdf} disabled={reading || busy}
          style={{ display: "block", marginBottom: 8 }} />
      </label>
      {reading && <p role="status">Reading PDF…</p>}
      <label>Or paste text
        <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={12}
          style={{ display: "block", width: "100%", padding: 8 }} />
      </label>
      <small className="muted">{content.length.toLocaleString()} / {MAX_CHARS.toLocaleString()} characters</small>
      <div>
        <button type="submit" disabled={disabled} style={{ marginTop: 8, padding: "8px 16px" }}>
          {busy ? "Reviewing..." : "Submit & review"}
        </button>
      </div>
      {notice && <p role="status">{notice}</p>}
      {error && <p role="alert" className="error">{error}</p>}
    </form>
  );
}
