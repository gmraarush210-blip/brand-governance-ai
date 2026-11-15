export const API = import.meta.env.VITE_API_URL ?? "";

async function handle(res) {
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail
        : Array.isArray(body.detail) ? body.detail.map((d) => d.msg).join("; ") : "";
    } catch { /* body was not JSON (proxy error page, 413, ...) */ }
    throw new Error(detail || `Request failed (${res.status} ${res.statusText || "error"})`);
  }
  try { return await res.json(); } catch { throw new Error("The server sent an unreadable response."); }
}

// fetch() rejects with a bare TypeError when the server is down or CORS blocks it.
async function request(path, init) {
  let res;
  try { res = await fetch(`${API}${path}`, init); }
  catch { throw new Error(`Cannot reach the API${API ? ` at ${API}` : ""}. Is the backend available?`); }
  return handle(res);
}

export const get = (path) => request(path);
export const postForm = (path, fields) => {
  const fd = new FormData();
  Object.entries(fields).forEach(([k, v]) => fd.append(k, v));
  return request(path, { method: "POST", body: fd });
};
export const postFile = (path, file) => {
  const fd = new FormData();
  fd.append("file", file);
  return request(path, { method: "POST", body: fd });
};
export const postJson = (path, body) =>
  request(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
