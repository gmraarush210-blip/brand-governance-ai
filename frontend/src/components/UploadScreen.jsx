import { useRef, useState } from "react";
import brandPack from "../../../data/fictional_brand_pack.json";
import { postFile, postForm } from "../api.js";

export const MAX_PDF_BYTES = 10 * 1024 * 1024;
export const MAX_CHARS = 10_000;

const CATEGORIES = ["Social Media", "Email Campaign", "Website Copy", "Press Release", "Product Brochure", "Advertisement"];

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
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("");
  const [busy, setBusy] = useState(false);
  const [reading, setReading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const fileInput = useRef(null);
  const inFlight = useRef(false);
  const created = useRef(null);
  const pdfSeq = useRef(0);

  async function processPdf(file, input) {
    if (!file) return;
    setError("");
    setNotice("");
    const problem = validatePdf(file);
    if (problem) {
      setError(problem);
      if (input) input.value = "";
      return;
    }
    const seq = ++pdfSeq.current;
    setReading(true);
    try {
      const data = await postFile("/api/submissions/upload-pdf", file);
      if (seq !== pdfSeq.current) return;
      setContent(data.text);
      setTitle(data.filename || file.name);
      setNotice(`Extracted text from ${file.name}. Review it below, then submit.`);
    } catch (err) {
      if (seq === pdfSeq.current) setError(String(err.message || err));
    } finally {
      if (seq === pdfSeq.current) setReading(false);
      if (input) input.value = "";
    }
  }

  function onPdf(event) {
    processPdf(event.target.files?.[0], event.target);
  }

  function onDrop(event) {
    event.preventDefault();
    setDragging(false);
    processPdf(event.dataTransfer.files?.[0]);
  }

  async function submit(event) {
    event?.preventDefault();
    if (inFlight.current) return;
    const text = content.trim();
    if (!title.trim()) { setError("Enter a document title."); return; }
    if (!category) { setError("Select a content category."); return; }
    if (!text) { setError("Paste some text or upload a PDF first."); return; }
    if (text.length > MAX_CHARS) { setError(`Draft is too long (${text.length.toLocaleString()} characters, max ${MAX_CHARS.toLocaleString()}).`); return; }
    const cleanTitle = title.trim();
    inFlight.current = true;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      let id = created.current && created.current.content === text && created.current.title === cleanTitle && created.current.category === category
        ? created.current.id : null;
      if (id === null) {
        const made = await postForm("/api/submissions", { content: text, title: cleanTitle, content_type: category });
        id = made.id;
        created.current = { id, content: text, title: cleanTitle, category };
      }
      await postForm(`/api/submissions/${id}/review`, {});
      created.current = null;
      onDone(id);
    } catch (err) {
      setError(`${String(err.message || err)} You can press Submit again; it will not create a duplicate.`);
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }

  const disabled = busy || reading || !content.trim() || !title.trim() || !category;

  return (
    <form className="surface-card submission-card" onSubmit={submit} noValidate aria-labelledby="submission-title">
      <div className="submission-heading">
        <h2 id="submission-title">New content submission</h2>
        <span className="review-mode">Rule-based review</span>
      </div>
      <p className="form-intro">Fields marked <strong>*</strong> are required.</p>
      <div className="field-grid">
        <label className="form-field" htmlFor="document-title">Document title <span>*</span>
          <input id="document-title" className="form-control" value={title} maxLength={120} placeholder="e.g. Spring launch email" required
            aria-invalid={!!error && !title.trim()} onChange={(event) => setTitle(event.target.value)} />
        </label>
        <label className="form-field" htmlFor="content-category">Content category <span>*</span>
          <select id="content-category" className="form-control" value={category} required
            aria-invalid={!!error && !category} onChange={(event) => setCategory(event.target.value)}>
            <option value="">Select a category</option>
            {CATEGORIES.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
      </div>
      <div className="text-field-wrap">
        <div className="field-label-row">
          <label className="form-field" htmlFor="marketing-copy">Marketing text</label>
          <button className="text-button" type="button" onClick={() => { setContent(brandPack.sample_content); setTitle((value) => value || "Spring launch email"); setCategory((value) => value || "Email Campaign"); setError(""); }}>Insert sample text</button>
        </div>
        <textarea id="marketing-copy" className="form-control copy-input" value={content} maxLength={MAX_CHARS}
          placeholder="Paste your copy here..." onChange={(event) => setContent(event.target.value)} />
        <div className="character-count" aria-live="polite">{content.length.toLocaleString()} / {MAX_CHARS.toLocaleString()}</div>
      </div>
      <div className="upload-field">
        <span className="form-field">Or upload a PDF</span>
        <div className={dragging ? "dropzone is-dragging" : "dropzone"} onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
          onDragOver={(event) => event.preventDefault()} onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setDragging(false); }} onDrop={onDrop}>
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 16V4m0 0L7 9m5-5 5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /><path d="M20 16v2a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>
          <p>Drag &amp; drop a PDF, or <button type="button" className="inline-link" onClick={() => fileInput.current?.click()}>browse files</button></p>
          <small>PDF only · up to 10 MB · images and video are not analysed</small>
          <input ref={fileInput} className="visually-hidden" type="file" accept="application/pdf,.pdf" onChange={onPdf} disabled={reading || busy} aria-label="Browse for a PDF" />
        </div>
      </div>
      {reading && <p role="status" className="form-status">Reading PDF…</p>}
      {notice && <p role="status" className="form-status">{notice}</p>}
      {error && <p role="alert" className="form-error">{error}</p>}
      <div className="submit-row">
        <p>Submitting starts a rule-based review. Nothing is approved or published automatically.</p>
        <button className="primary-button" type="submit" disabled={disabled}>
          {busy ? "Reviewing…" : "Submit for Review"}
        </button>
      </div>
    </form>
  );
}
