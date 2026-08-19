import { useEffect, useState } from "react";

type PreviewPayload = {
  kind: string;
  name: string;
  suffix: string;
  size_bytes: number;
  headers?: string[];
  rows?: string[][];
  sheet?: string;
  sheets?: string[];
  records?: Array<{ header: string; sequence: string; length: number }>;
  data?: unknown;
  text?: string;
  error?: string;
};

function localFileUrl(slug: string, path: string) {
  return `/api/projects/${encodeURIComponent(slug)}/files/${path.split("/").map(encodeURIComponent).join("/")}`;
}

function previewUrl(slug: string, path: string) {
  return `/api/projects/${encodeURIComponent(slug)}/preview/${path.split("/").map(encodeURIComponent).join("/")}`;
}

function FilePreviewModal({ slug, path, onClose }: { slug: string; path: string; onClose: () => void }) {
  const [preview, setPreview] = useState<PreviewPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(previewUrl(slug, path))
      .then(async (response) => {
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.detail ?? "Could not preview file.");
        return payload as PreviewPayload;
      })
      .then(setPreview)
      .catch((err: Error) => setError(err.message));
  }, [slug, path]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const raw = localFileUrl(slug, path);
  return <div className="modal-backdrop file-preview-backdrop"><section className="modal-dialog file-preview-dialog" role="dialog" aria-modal="true">
    <div className="modal-header"><div><p className="eyebrow">Scientific file</p><h2>{preview?.name ?? path.split("/").pop()}</h2>{preview && <p className="muted">{preview.kind} · {(preview.size_bytes / 1024).toFixed(1)} KB</p>}</div><button className="icon-button" onClick={onClose}>×</button></div>
    <div className="file-preview-body">
      {!preview && !error && <p className="muted">Reading local file…</p>}
      {error && <p className="form-error">{error}</p>}
      {preview?.kind === "image" && <div className="image-preview"><img src={raw} alt={preview.name} /><p className="muted">TIFF display depends on browser support; the original file is always preserved.</p></div>}
      {preview?.kind === "pdf" && <iframe className="pdf-preview" src={raw} title={preview.name} />}
      {preview?.kind === "structure" && <div className="structure-file-preview"><p>This molecular structure can be opened with the design's PyMOL controls.</p><code>{path}</code></div>}
      {(preview?.kind === "table" || preview?.kind === "spreadsheet" || preview?.kind === "rosetta_score") && <div className="energy-table-wrap scientific-table-preview">{preview.sheet && <p className="muted">Sheet: {preview.sheet}{preview.sheets && preview.sheets.length > 1 ? ` · ${preview.sheets.length} sheets` : ""}</p>}<table className="energy-table"><thead><tr>{(preview.headers ?? []).map((header, index) => <th key={`${header}-${index}`}>{header || `Column ${index + 1}`}</th>)}</tr></thead><tbody>{(preview.rows ?? []).map((row, rowIndex) => <tr key={rowIndex}>{row.map((value, index) => <td key={index}>{value}</td>)}</tr>)}</tbody></table></div>}
      {preview?.kind === "fasta" && <div className="fasta-preview">{(preview.records ?? []).map((record, index) => <article className="record-card" key={`${record.header}-${index}`}><div className="record-title"><strong>{record.header}</strong><span>{record.length} aa</span></div><pre className="sequence">{record.sequence}</pre></article>)}</div>}
      {preview?.kind === "json" && <pre className="code-preview">{preview.error ? `${preview.error}\n\n${preview.text ?? ""}` : JSON.stringify(preview.data, null, 2)}</pre>}
      {preview?.kind === "text" && <pre className="code-preview">{preview.text}</pre>}
      {preview?.kind === "generic" && <p className="muted">HGD preserves this file as evidence but does not have a native preview for {preview.suffix || "this format"} yet.</p>}
    </div>
    <div className="modal-actions"><a className="secondary-button" href={raw} target="_blank" rel="noreferrer">Open original ↗</a><button className="primary-button" onClick={onClose}>Close</button></div>
  </section></div>;
}

export function EvidenceFiles({ slug, paths }: { slug: string; paths: string[] }) {
  const [previewPath, setPreviewPath] = useState<string | null>(null);
  return <><div className="attached-files">{paths.map((path) => {
    const name = path.split("/").pop() ?? path;
    return <div key={path} className="local-file-link scientific-file-link"><button className="file-preview-button" onClick={() => setPreviewPath(path)}><span className="file-icon">⌕</span><span><b>{name}</b><small>{path}</small></span></button><a href={localFileUrl(slug, path)} target="_blank" rel="noreferrer" title="Open original">↗</a></div>;
  })}</div>{previewPath && <FilePreviewModal slug={slug} path={previewPath} onClose={() => setPreviewPath(null)} />}</>;
}
