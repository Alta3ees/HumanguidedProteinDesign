import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import type { DesignNode, EvidenceEntry, ProjectDetail, ProjectListItem } from "./types";

type PositionedNode = { node: DesignNode; x: number; y: number; depth: number };
type Edge = { from: PositionedNode; to: PositionedNode };

function findDesign(nodes: DesignNode[], id: string | null): DesignNode | null {
  if (!id) return null;
  for (const node of nodes) {
    if (node.id === id) return node;
    const child = findDesign(node.children, id);
    if (child) return child;
  }
  return null;
}

function firstDesign(nodes: DesignNode[]): DesignNode | null {
  return nodes[0] ?? null;
}

function StatusBadge({ value }: { value: string }) {
  return <span className={`badge badge-${value}`}>{value}</span>;
}

function subtreeWeight(node: DesignNode): number {
  if (node.children.length === 0) return 1;
  return node.children.reduce((sum, child) => sum + subtreeWeight(child), 0);
}

function treeDepth(node: DesignNode): number {
  if (node.children.length === 0) return 0;
  return 1 + Math.max(...node.children.map(treeDepth));
}

function layoutRadial(roots: DesignNode[]) {
  const positioned: PositionedNode[] = [];
  const edges: Edge[] = [];
  const ringGap = 195;
  const nodeMargin = 130;
  const maxDepth = roots.length === 0 ? 0 : Math.max(...roots.map(treeDepth)) + (roots.length > 1 ? 1 : 0);
  const radius = Math.max(260, maxDepth * ringGap + nodeMargin);
  const size = Math.max(760, radius * 2);
  const center = size / 2;

  function place(node: DesignNode, depth: number, startAngle: number, endAngle: number): PositionedNode {
    const angle = (startAngle + endAngle) / 2;
    const radialDistance = depth * ringGap;
    const current: PositionedNode = {
      node,
      x: center + Math.cos(angle) * radialDistance,
      y: center + Math.sin(angle) * radialDistance,
      depth,
    };
    positioned.push(current);

    if (node.children.length > 0) {
      const totalWeight = node.children.reduce((sum, child) => sum + subtreeWeight(child), 0);
      let cursor = startAngle;
      for (const child of node.children) {
        const share = (endAngle - startAngle) * (subtreeWeight(child) / totalWeight);
        const childPosition = place(child, depth + 1, cursor, cursor + share);
        edges.push({ from: current, to: childPosition });
        cursor += share;
      }
    }

    return current;
  }

  if (roots.length === 1) {
    place(roots[0], 0, -Math.PI, Math.PI);
  } else if (roots.length > 1) {
    const totalWeight = roots.reduce((sum, root) => sum + subtreeWeight(root), 0);
    let cursor = -Math.PI;
    for (const root of roots) {
      const share = 2 * Math.PI * (subtreeWeight(root) / totalWeight);
      place(root, 1, cursor, cursor + share);
      cursor += share;
    }
  }

  return { positioned, edges, size, center, maxDepth };
}

function Mindmap({
  roots,
  selectedId,
  onSelect,
}: {
  roots: DesignNode[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const layout = useMemo(() => layoutRadial(roots), [roots]);

  if (roots.length === 0) {
    return <div className="empty-panel">This project has an objective but no designs yet.</div>;
  }

  return (
    <div className="mindmap-scroll">
      <div className="mindmap radial-map" style={{ width: layout.size, height: layout.size }}>
        <svg className="mindmap-edges" width={layout.size} height={layout.size} aria-hidden="true">
          {Array.from({ length: layout.maxDepth }, (_, index) => {
            const radius = (index + 1) * 195;
            return <circle key={radius} className="generation-ring" cx={layout.center} cy={layout.center} r={radius} />;
          })}
          {layout.edges.map(({ from, to }) => (
            <path
              key={`${from.node.id}-${to.node.id}`}
              className="lineage-edge"
              d={`M ${from.x} ${from.y} L ${to.x} ${to.y}`}
            />
          ))}
        </svg>

        {layout.positioned.map(({ node, x, y, depth }) => {
          const outcome = node.decision?.outcome ?? "none";
          const evidenceTotal = Object.values(node.evidence_counts).reduce((sum, count) => sum + count, 0);
          return (
            <button
              key={node.id}
              className={`mindmap-node radial-node status-${node.status} decision-${outcome} ${selectedId === node.id ? "selected" : ""}`}
              style={{ left: x, top: y }}
              onClick={() => onSelect(node.id)}
              title={`Generation ${depth}: ${node.lineage_label}`}
            >
              <div className="node-title">{node.label}</div>
              <div className="node-subtitle">{node.metadata?.mutation ? String(node.metadata.mutation) : node.origin}</div>
              <div className="node-stats">
                <span>{node.sequence ? `${node.sequence.length} aa` : "no seq"}</span>
                <span>{node.structures.length} str</span>
                <span>{evidenceTotal} ev</span>
              </div>
              <div className="node-outcome">{outcome}</div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function RosettaCard({ entry }: { entry: EvidenceEntry }) {
  const data = entry.data ?? {};
  const scoreTerms = (data.score_terms ?? {}) as Record<string, number>;
  const previous = typeof data.previous_score === "number" ? data.previous_score : null;
  const mutant = typeof data.mutant_score === "number" ? data.mutant_score : null;
  const delta = typeof data.delta_score === "number" ? data.delta_score : null;

  return (
    <article className="record-card rosetta-card">
      <div className="record-title">
        <strong>{entry.source_name}</strong>
        <span>{String(data.mutation ?? "computational evaluation")}</span>
      </div>
      <div className="score-grid">
        {previous != null && <div><span>Parent score</span><b>{previous.toFixed(2)}</b></div>}
        {mutant != null && <div><span>Design score</span><b>{mutant.toFixed(2)}</b></div>}
        {delta != null && <div><span>ΔScore</span><b className={delta <= 0 ? "score-good" : "score-bad"}>{delta >= 0 ? "+" : ""}{delta.toFixed(2)} REU</b></div>}
      </div>
      {Object.keys(scoreTerms).length > 0 && (
        <details>
          <summary>Rosetta score terms</summary>
          <div className="term-grid">
            {Object.entries(scoreTerms).map(([term, value]) => (
              <div key={term}><span>{term}</span><b>{Number(value).toFixed(2)}</b></div>
            ))}
          </div>
        </details>
      )}
    </article>
  );
}

function localFileUrl(slug: string, path: string): string {
  const encodedPath = path.split("/").map((part) => encodeURIComponent(part)).join("/");
  return `/api/projects/${encodeURIComponent(slug)}/files/${encodedPath}`;
}

function EvidenceFiles({ slug, paths }: { slug: string; paths: string[] }) {
  return (
    <div className="attached-files">
      {paths.map((path) => {
        const name = path.split("/").pop() ?? path;
        return (
          <a key={path} className="local-file-link" href={localFileUrl(slug, path)} target="_blank" rel="noreferrer">
            <span className="file-icon">↗</span>
            <span><b>{name}</b><small>{path}</small></span>
          </a>
        );
      })}
    </div>
  );
}

function EvidenceImporter({
  slug,
  design,
  onImported,
}: {
  slug: string;
  design: DesignNode;
  onImported: (project: ProjectDetail) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [sourceType, setSourceType] = useState("experimental");
  const [sourceName, setSourceName] = useState("");
  const [summary, setSummary] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (files.length === 0) {
      setMessage("Choose at least one local file.");
      return;
    }
    const body = new FormData();
    body.append("source_type", sourceType);
    body.append("source_name", sourceName);
    body.append("summary", summary);
    body.append("notes", notes);
    files.forEach((file) => body.append("files", file));

    setBusy(true);
    setMessage(null);
    try {
      const response = await fetch(`/api/projects/${encodeURIComponent(slug)}/designs/${encodeURIComponent(design.id)}/evidence`, {
        method: "POST",
        body,
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail ?? "Import failed.");
      }
      const payload = await response.json();
      onImported(payload.project as ProjectDetail);
      const importedCount = Array.isArray(payload.stored_files) ? payload.stored_files.length : files.length;
      setFiles([]);
      setSourceName("");
      setSummary("");
      setNotes("");
      if (inputRef.current) inputRef.current.value = "";
      setMessage(`Attached ${importedCount} local file${importedCount === 1 ? "" : "s"}. Evidence updated above.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Import failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="import-section">
      <div className="section-heading compact">
        <div>
          <p className="eyebrow">Local data</p>
          <h3>Import evidence</h3>
        </div>
      </div>
      <form className="import-form" onSubmit={submit}>
        <div className="form-row">
          <label>Type
            <select value={sourceType} onChange={(event) => setSourceType(event.target.value)}>
              <option value="computational">Computational</option>
              <option value="experimental">Experimental</option>
              <option value="literature">Literature</option>
              <option value="note">Note</option>
            </select>
          </label>
          <label>Source <span className="optional-label">optional</span>
            <input value={sourceName} onChange={(event) => setSourceName(event.target.value)} placeholder="NMR, SEC, paper…" />
          </label>
        </div>
        <label>Summary <span className="optional-label">optional</span>
          <textarea value={summary} onChange={(event) => setSummary(event.target.value)} placeholder="Leave blank to use the filename automatically." />
        </label>
        <label>Notes <span className="optional-label">optional</span>
          <textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Interpretation or context" />
        </label>
        <input ref={inputRef} type="file" multiple onChange={(event) => setFiles(Array.from(event.target.files ?? []))} />
        <div className="upload-zone" onClick={() => inputRef.current?.click()}>
          <b>{files.length > 0 ? `${files.length} file${files.length === 1 ? "" : "s"} selected` : "Browse local files"}</b>
          <span>NMR spectra, CSV, images, PDFs, raw instrument files, model outputs…</span>
        </div>
        {files.length > 0 && <div className="file-list">{files.map((file) => <span key={`${file.name}-${file.size}`}>{file.name}</span>)}</div>}
        <button className="primary-button" type="submit" disabled={busy || files.length === 0}>{busy ? "Importing…" : "Attach evidence"}</button>
        {message && <p className="form-message">{message}</p>}
      </form>
    </section>
  );
}

function DesignInspector({
  design,
  slug,
  onImported,
}: {
  design: DesignNode | null;
  slug: string | null;
  onImported: (project: ProjectDetail) => void;
}) {
  if (!design) return <div className="empty-panel">Select a design to inspect its scientific record.</div>;
  const computational = design.evidence.filter((entry) => entry.source_type === "computational" && entry.data && Object.keys(entry.data).length > 0);

  return (
    <div className="inspector-content">
      <div className="section-heading">
        <div><p className="eyebrow">Design</p><h2>{design.label}</h2></div>
        <StatusBadge value={design.status} />
      </div>
      <dl className="facts-grid">
        <div><dt>Origin</dt><dd>{design.origin}</dd></div>
        <div><dt>Decision</dt><dd>{design.decision?.outcome ?? "none"}</dd></div>
        <div><dt>Structures</dt><dd>{design.structures.length}</dd></div>
        <div><dt>Created</dt><dd>{design.created_at.slice(0, 10)}</dd></div>
      </dl>
      <section><h3>Lineage</h3><p className="lineage">{design.lineage_label}</p></section>
      <section><h3>Sequence</h3>{design.sequence ? <pre className="sequence">{design.sequence}</pre> : <p className="muted">No sequence is assigned to this design.</p>}</section>
      {design.hypothesis && <section><h3>Hypothesis</h3><p>{design.hypothesis}</p></section>}
      {design.decision && <section><h3>Human decision</h3><div className="record-card"><strong>{design.decision.outcome}</strong><p><b>Objective:</b> {design.decision.objective}</p><p><b>Hypothesis:</b> {design.decision.hypothesis}</p>{design.decision.rationale && <p><b>Rationale:</b> {design.decision.rationale}</p>}</div></section>}
      {computational.length > 0 && <section><h3>Computational evaluation</h3><div className="record-list">{computational.map((entry) => <RosettaCard key={entry.id} entry={entry} />)}</div></section>}
      <section><h3>Structural hypotheses</h3>{design.structures.length === 0 ? <p className="muted">No structure attached.</p> : <div className="record-list">{design.structures.map((structure) => <article className="record-card" key={structure.id}><div className="record-title"><strong>{structure.source}</strong><span className="mono">{structure.structure_path}</span></div>{structure.method && <p>{structure.method}</p>}<div className="metrics">{structure.mean_plddt != null && <span>pLDDT {structure.mean_plddt.toFixed(1)}</span>}{structure.ptm != null && <span>pTM {structure.ptm.toFixed(2)}</span>}{structure.iptm != null && <span>ipTM {structure.iptm.toFixed(2)}</span>}</div></article>)}</div>}</section>
      <section>
        <h3>Evidence</h3>
        <div className="evidence-strip">{Object.entries(design.evidence_counts).map(([kind, count]) => <span key={kind}><b>{count}</b> {kind}</span>)}</div>
        {design.evidence.length > 0 && <div className="record-list">{design.evidence.map((entry) => (
          <article className="record-card" key={entry.id}>
            <div className="record-title"><strong>{entry.source_name}</strong><span>{entry.source_type}</span></div>
            <p>{entry.summary}</p>
            {entry.notes && <p className="muted">{entry.notes}</p>}
            {slug && entry.file_paths && entry.file_paths.length > 0 && <EvidenceFiles slug={slug} paths={entry.file_paths} />}
          </article>
        ))}</div>}
      </section>
      {slug && <EvidenceImporter slug={slug} design={design} onImported={onImported} />}
    </div>
  );
}

export default function App() {
  const [projects, setProjects] = useState<ProjectListItem[]>([]);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [selectedDesignId, setSelectedDesignId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/projects")
      .then((response) => { if (!response.ok) throw new Error("Could not load projects."); return response.json(); })
      .then((data: ProjectListItem[]) => { setProjects(data); if (data.length > 0) setSelectedSlug(data[0].slug); })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedSlug) { setProject(null); return; }
    setLoading(true);
    setError(null);
    fetch(`/api/projects/${encodeURIComponent(selectedSlug)}`)
      .then((response) => { if (!response.ok) throw new Error("Could not load project archive."); return response.json(); })
      .then((data: ProjectDetail) => { setProject(data); setSelectedDesignId(firstDesign(data.design_tree)?.id ?? null); })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [selectedSlug]);

  const selectedDesign = useMemo(() => findDesign(project?.design_tree ?? [], selectedDesignId), [project, selectedDesignId]);

  function handleImported(updated: ProjectDetail) {
    setProject(updated);
    setProjects((items) => items.map((item) => item.slug === updated.slug ? { ...item, evidence_count: updated.counts.evidence } : item));
  }

  return (
    <main className="app-shell">
      <header className="topbar"><div><p className="eyebrow">Human-Guided Protein Design</p><h1>Research workspace</h1></div><div className="topbar-meta"><span className="local-pill">Local only</span><span className="version">v0.4 dev</span></div></header>
      <div className="workspace">
        <aside className="sidebar"><div className="panel-title"><span>Projects</span><span className="count">{projects.length}</span></div>{projects.map((item) => <button key={item.slug} className={`project-button ${selectedSlug === item.slug ? "active" : ""}`} onClick={() => setSelectedSlug(item.slug)}><strong>{item.name}</strong><span>{item.design_count} designs · {item.structure_count} structures · {item.evidence_count} evidence</span></button>)}{!loading && projects.length === 0 && <p className="muted">No projects found in data/projects.</p>}</aside>
        <section className="canvas">{error && <div className="error-banner">{error}</div>}{loading && !project && <div className="empty-panel">Loading workspace…</div>}{project && <><div className="project-header"><div><p className="eyebrow">Project</p><h2>{project.name}</h2></div><div className="project-counts"><span><b>{project.counts.designs}</b> designs</span><span><b>{project.counts.structures}</b> structures</span><span><b>{project.counts.evidence}</b> evidence</span></div></div>{project.objectives.length > 0 && <div className="objective-card"><span className="eyebrow">Scientific objective</span><p>{project.objectives[0].description}</p>{project.objectives[0].constraints.length > 0 && <div className="chips">{project.objectives[0].constraints.map((constraint) => <span key={constraint}>{constraint}</span>)}</div>}</div>}<div className="tree-panel"><div className="panel-title"><span>Radial design map</span><span className="muted">WT center · generations expand outward</span></div><Mindmap roots={project.design_tree} selectedId={selectedDesignId} onSelect={setSelectedDesignId} /></div></>}</section>
        <aside className="inspector"><DesignInspector design={selectedDesign} slug={selectedSlug} onImported={handleImported} /></aside>
      </div>
    </main>
  );
}
