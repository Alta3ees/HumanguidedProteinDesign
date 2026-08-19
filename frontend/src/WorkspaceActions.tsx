import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import type { DesignNode, ProjectDetail } from "./types";

async function responseJson(response: Response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail ?? "Request failed.");
  return payload;
}

export function NewProjectDialog({ open, onClose, onCreated }: {
  open: boolean;
  onClose: () => void;
  onCreated: (project: ProjectDetail, listItem: Record<string, unknown>) => void;
}) {
  const [name, setName] = useState("");
  const [objective, setObjective] = useState("");
  const [sequence, setSequence] = useState("");
  const [designName, setDesignName] = useState("");
  const [targetName, setTargetName] = useState("");
  const [targetSequence, setTargetSequence] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  if (!open) return null;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setMessage(null);
    try {
      const payload = await responseJson(await fetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, objective, sequence: sequence || null, design_name: designName || null, target_name: targetName || null, target_sequence: targetSequence || null }),
      }));
      onCreated(payload.project as ProjectDetail, payload.list_item as Record<string, unknown>);
      setName(""); setObjective(""); setSequence(""); setDesignName(""); setTargetName(""); setTargetSequence("");
      onClose();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not create project.");
    } finally { setBusy(false); }
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal-dialog" role="dialog" aria-modal="true" aria-label="Create project">
        <div className="modal-header"><div><p className="eyebrow">Workspace action</p><h2>New project</h2></div><button className="icon-button" onClick={onClose}>×</button></div>
        <form className="action-form" onSubmit={submit}>
          <label>Project name<input value={name} onChange={(e) => setName(e.target.value)} required /></label>
          <label>Scientific objective<textarea value={objective} onChange={(e) => setObjective(e.target.value)} required /></label>
          <div className="form-section-label">Optional starting design</div>
          <label>Design name<input value={designName} onChange={(e) => setDesignName(e.target.value)} placeholder="Starting sequence" /></label>
          <label>Protein sequence<textarea className="mono" value={sequence} onChange={(e) => setSequence(e.target.value)} placeholder="Leave blank for objective-only project" /></label>
          <div className="form-section-label">Optional binder target</div>
          <label>Target name<input value={targetName} onChange={(e) => setTargetName(e.target.value)} /></label>
          <label>Target sequence<textarea className="mono" value={targetSequence} onChange={(e) => setTargetSequence(e.target.value)} /></label>
          {message && <p className="form-error">{message}</p>}
          <div className="modal-actions"><button type="button" className="secondary-button" onClick={onClose}>Cancel</button><button className="primary-button" disabled={busy}>{busy ? "Creating…" : "Create project"}</button></div>
        </form>
      </section>
    </div>
  );
}

export function RegisterDesignDialog({ open, onClose, slug, designs, defaultParentId, onUpdated }: {
  open: boolean;
  onClose: () => void;
  slug: string;
  designs: DesignNode[];
  defaultParentId: string | null;
  onUpdated: (project: ProjectDetail, designId: string) => void;
}) {
  const [name, setName] = useState("");
  const [origin, setOrigin] = useState("imported_design");
  const [sequence, setSequence] = useState("");
  const [parentId, setParentId] = useState("");
  const [hypothesis, setHypothesis] = useState("");
  const [sourceTool, setSourceTool] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const validDefault = defaultParentId && designs.some((design) => design.id === defaultParentId)
      ? defaultParentId
      : "";
    setParentId(validDefault);
    setMessage(null);
  }, [open, slug, defaultParentId]);

  if (!open) return null;

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage(null);
    try {
      const validParentId = parentId && designs.some((design) => design.id === parentId)
        ? parentId
        : null;
      const payload = await responseJson(await fetch(`/api/projects/${encodeURIComponent(slug)}/designs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, origin, sequence: sequence || null, parent_design_id: validParentId, hypothesis: hypothesis || null, source_tool: sourceTool || null }),
      }));
      onUpdated(payload.project as ProjectDetail, payload.design_id as string);
      setName(""); setSequence(""); setHypothesis(""); setSourceTool(""); setParentId("");
      onClose();
    } catch (error) { setMessage(error instanceof Error ? error.message : "Could not register design."); }
    finally { setBusy(false); }
  }

  return (
    <div className="modal-backdrop">
      <section className="modal-dialog" role="dialog" aria-modal="true" aria-label="Register design">
        <div className="modal-header"><div><p className="eyebrow">Workspace action</p><h2>Register design</h2></div><button className="icon-button" onClick={onClose}>×</button></div>
        <form className="action-form" onSubmit={submit}>
          <p className="muted">Adds a new design node to <b>{slug}</b>.</p>
          <div className="two-col-form"><label>Name<input value={name} onChange={(e) => setName(e.target.value)} required /></label><label>Origin<select value={origin} onChange={(e) => setOrigin(e.target.value)}><option value="imported_design">Imported design</option><option value="sequence_design">Sequence design</option><option value="generated_backbone">Generated backbone</option><option value="de_novo">De novo</option><option value="point_mutation">Point mutation</option><option value="natural_sequence">Natural sequence</option></select></label></div>
          <label>Parent<select value={parentId} onChange={(e) => setParentId(e.target.value)}><option value="">No parent</option>{designs.map((design) => <option key={design.id} value={design.id}>{design.lineage_label}</option>)}</select></label>
          <label>Sequence <span className="optional-label">optional</span><textarea className="mono" value={sequence} onChange={(e) => setSequence(e.target.value)} /></label>
          <label>Hypothesis <span className="optional-label">optional</span><textarea value={hypothesis} onChange={(e) => setHypothesis(e.target.value)} /></label>
          <label>Generator / source tool <span className="optional-label">optional</span><input value={sourceTool} onChange={(e) => setSourceTool(e.target.value)} placeholder="RFdiffusion, ProteinMPNN, imported..." /></label>
          {message && <p className="form-error">{message}</p>}
          <div className="modal-actions"><button type="button" className="secondary-button" onClick={onClose}>Cancel</button><button className="primary-button" disabled={busy}>{busy ? "Registering…" : "Register design"}</button></div>
        </form>
      </section>
    </div>
  );
}

export function AttachStructureDialog({ open, onClose, slug, design, onUpdated }: {
  open: boolean;
  onClose: () => void;
  slug: string;
  design: DesignNode;
  onUpdated: (project: ProjectDetail) => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [source, setSource] = useState("user");
  const [method, setMethod] = useState("");
  const [plddt, setPlddt] = useState("");
  const [ptm, setPtm] = useState("");
  const [iptm, setIptm] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  if (!open) return null;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file) { setMessage("Choose a PDB/CIF/mmCIF file."); return; }
    const body = new FormData();
    body.append("file", file); body.append("source", source); body.append("method", method); body.append("notes", notes);
    if (plddt) body.append("mean_plddt", plddt); if (ptm) body.append("ptm", ptm); if (iptm) body.append("iptm", iptm);
    setBusy(true); setMessage(null);
    try {
      const payload = await responseJson(await fetch(`/api/projects/${encodeURIComponent(slug)}/designs/${encodeURIComponent(design.id)}/structures`, { method: "POST", body }));
      onUpdated(payload.project as ProjectDetail); setFile(null); setMethod(""); setPlddt(""); setPtm(""); setIptm(""); setNotes("");
      if (fileRef.current) fileRef.current.value = "";
      onClose();
    } catch (error) { setMessage(error instanceof Error ? error.message : "Could not attach structure."); }
    finally { setBusy(false); }
  }

  return (
    <div className="modal-backdrop">
      <section className="modal-dialog" role="dialog" aria-modal="true" aria-label="Attach structure">
        <div className="modal-header"><div><p className="eyebrow">{design.label}</p><h2>Attach structure</h2></div><button className="icon-button" onClick={onClose}>×</button></div>
        <form className="action-form" onSubmit={submit}>
          <input ref={fileRef} type="file" accept=".pdb,.cif,.mmcif" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          <div className="two-col-form"><label>Source<select value={source} onChange={(e) => setSource(e.target.value)}><option value="experimental">Experimental</option><option value="alphafold">AlphaFold</option><option value="colabfold">ColabFold</option><option value="rfdiffusion">RFdiffusion</option><option value="rosetta">Rosetta</option><option value="user">User</option><option value="other">Other</option></select></label><label>Method / model<input value={method} onChange={(e) => setMethod(e.target.value)} /></label></div>
          <div className="three-col-form"><label>Mean pLDDT<input type="number" min="0" max="100" step="0.1" value={plddt} onChange={(e) => setPlddt(e.target.value)} /></label><label>pTM<input type="number" min="0" max="1" step="0.01" value={ptm} onChange={(e) => setPtm(e.target.value)} /></label><label>ipTM<input type="number" min="0" max="1" step="0.01" value={iptm} onChange={(e) => setIptm(e.target.value)} /></label></div>
          <label>Notes<textarea value={notes} onChange={(e) => setNotes(e.target.value)} /></label>
          {message && <p className="form-error">{message}</p>}
          <div className="modal-actions"><button type="button" className="secondary-button" onClick={onClose}>Cancel</button><button className="primary-button" disabled={busy || !file}>{busy ? "Attaching…" : "Attach structure"}</button></div>
        </form>
      </section>
    </div>
  );
}

function diffPositions(original: string | null | undefined, edited: string) {
  if (!original) return new Set<number>();
  const positions = new Set<number>();
  const max = Math.max(original.length, edited.length);
  for (let i = 0; i < max; i += 1) if (original[i] !== edited[i]) positions.add(i);
  return positions;
}

export function SequenceEditor({ slug, design, onUpdated }: {
  slug: string;
  design: DesignNode;
  onUpdated: (project: ProjectDetail, designId: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [sequence, setSequence] = useState(design.sequence ?? "");
  const [name, setName] = useState(`${design.label} edited`);
  const [hypothesis, setHypothesis] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const changed = useMemo(() => diffPositions(design.sequence, sequence.replace(/\s+/g, "").toUpperCase()), [design.sequence, sequence]);
  const normalizedPreview = sequence.replace(/\s+/g, "").toUpperCase();

  async function save() {
    setBusy(true); setMessage(null);
    try {
      const payload = await responseJson(await fetch(`/api/projects/${encodeURIComponent(slug)}/designs/${encodeURIComponent(design.id)}/derive-sequence`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ sequence, name: name || null, hypothesis: hypothesis || null }),
      }));
      onUpdated(payload.project as ProjectDetail, payload.design_id as string);
      setEditing(false);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Could not save sequence design."); }
    finally { setBusy(false); }
  }

  if (!editing) {
    return <button className="secondary-button" onClick={() => { setSequence(design.sequence ?? ""); setEditing(true); }}>Edit sequence / create child</button>;
  }

  return (
    <div className="sequence-editor">
      <div className="sequence-editor-header"><div><p className="eyebrow">Provenance-safe editor</p><h3>Create derived sequence</h3></div><button className="icon-button" onClick={() => setEditing(false)}>×</button></div>
      <p className="muted">The selected historical node will not be overwritten. Saving creates a child design.</p>
      <textarea className="sequence-textarea mono" value={sequence} onChange={(e) => setSequence(e.target.value)} spellCheck={false} />
      <div className="sequence-preview" aria-label="Sequence change preview">
        {normalizedPreview.split("").map((aa, index) => <span key={index} className={changed.has(index) ? "changed-residue" : ""} title={changed.has(index) ? `Position ${index + 1}: ${design.sequence?.[index] ?? "∅"} → ${aa}` : `Position ${index + 1}`}>{aa}</span>)}
      </div>
      <div className="sequence-change-summary">{changed.size} changed position{changed.size === 1 ? "" : "s"}{design.sequence && normalizedPreview.length !== design.sequence.length ? ` · length ${design.sequence.length} → ${normalizedPreview.length}` : ""}</div>
      <div className="two-col-form"><label>New design name<input value={name} onChange={(e) => setName(e.target.value)} /></label><label>Hypothesis<input value={hypothesis} onChange={(e) => setHypothesis(e.target.value)} placeholder="What is this sequence meant to test?" /></label></div>
      {message && <p className="form-error">{message}</p>}
      <div className="modal-actions"><button className="secondary-button" onClick={() => setEditing(false)}>Cancel</button><button className="primary-button" onClick={save} disabled={busy || changed.size === 0}>{busy ? "Saving…" : "Save as derived design"}</button></div>
    </div>
  );
}

export function DeleteEvidenceButton({ slug, evidenceId, hasFiles, onDeleted }: {
  slug: string;
  evidenceId: string;
  hasFiles: boolean;
  onDeleted: (project: ProjectDetail) => void;
}) {
  const [busy, setBusy] = useState(false);
  async function remove() {
    const question = hasFiles
      ? "Delete this evidence entry and its copied local evidence file(s)? Structure files are never deleted by this action."
      : "Delete this evidence entry?";
    if (!window.confirm(question)) return;
    setBusy(true);
    try {
      const payload = await responseJson(await fetch(`/api/projects/${encodeURIComponent(slug)}/evidence/${encodeURIComponent(evidenceId)}`, { method: "DELETE" }));
      onDeleted(payload.project as ProjectDetail);
    } catch (error) { window.alert(error instanceof Error ? error.message : "Could not delete evidence."); }
    finally { setBusy(false); }
  }
  return <button className="delete-evidence-button" onClick={remove} disabled={busy} title="Delete evidence">{busy ? "…" : "×"}</button>;
}
