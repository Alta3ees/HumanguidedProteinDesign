import { useEffect, useMemo, useState } from "react";
import type { DesignNode, ProjectDetail, ProjectListItem } from "./types";

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

function TreeNode({
  node,
  selectedId,
  onSelect,
}: {
  node: DesignNode;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const outcome = node.decision?.outcome ?? "none";
  const evidenceTotal = Object.values(node.evidence_counts).reduce((sum, count) => sum + count, 0);

  return (
    <li className="tree-item">
      <button
        className={`design-card ${selectedId === node.id ? "selected" : ""}`}
        onClick={() => onSelect(node.id)}
      >
        <div className="design-card-topline">
          <strong>{node.label}</strong>
          <StatusBadge value={node.status} />
        </div>
        <span className="mono muted">{node.origin}</span>
        <div className="design-card-meta">
          <span>{node.sequence ? `${node.sequence.length} aa` : "no sequence"}</span>
          <span>{node.structures.length} structure{node.structures.length === 1 ? "" : "s"}</span>
          <span>{evidenceTotal} evidence</span>
          <span>{outcome}</span>
        </div>
      </button>

      {node.children.length > 0 && (
        <ul className="tree-children">
          {node.children.map((child) => (
            <TreeNode key={child.id} node={child} selectedId={selectedId} onSelect={onSelect} />
          ))}
        </ul>
      )}
    </li>
  );
}

function DesignInspector({ design }: { design: DesignNode | null }) {
  if (!design) {
    return <div className="empty-panel">Select a design to inspect its scientific record.</div>;
  }

  return (
    <div className="inspector-content">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Design</p>
          <h2>{design.label}</h2>
        </div>
        <StatusBadge value={design.status} />
      </div>

      <dl className="facts-grid">
        <div><dt>Origin</dt><dd>{design.origin}</dd></div>
        <div><dt>Decision</dt><dd>{design.decision?.outcome ?? "none"}</dd></div>
        <div><dt>Structures</dt><dd>{design.structures.length}</dd></div>
        <div><dt>Created</dt><dd>{design.created_at.slice(0, 10)}</dd></div>
      </dl>

      <section>
        <h3>Lineage</h3>
        <p className="lineage">{design.lineage_label}</p>
      </section>

      <section>
        <h3>Sequence</h3>
        {design.sequence ? (
          <pre className="sequence">{design.sequence}</pre>
        ) : (
          <p className="muted">No sequence is assigned to this design.</p>
        )}
      </section>

      {design.hypothesis && (
        <section>
          <h3>Hypothesis</h3>
          <p>{design.hypothesis}</p>
        </section>
      )}

      {design.decision && (
        <section>
          <h3>Human decision</h3>
          <div className="record-card">
            <strong>{design.decision.outcome}</strong>
            <p><b>Objective:</b> {design.decision.objective}</p>
            <p><b>Hypothesis:</b> {design.decision.hypothesis}</p>
            {design.decision.rationale && <p><b>Rationale:</b> {design.decision.rationale}</p>}
          </div>
        </section>
      )}

      <section>
        <h3>Structural hypotheses</h3>
        {design.structures.length === 0 ? (
          <p className="muted">No structure attached.</p>
        ) : (
          <div className="record-list">
            {design.structures.map((structure) => (
              <article className="record-card" key={structure.id}>
                <div className="record-title">
                  <strong>{structure.source}</strong>
                  <span className="mono">{structure.structure_path}</span>
                </div>
                {structure.method && <p>{structure.method}</p>}
                <div className="metrics">
                  {structure.mean_plddt != null && <span>pLDDT {structure.mean_plddt.toFixed(1)}</span>}
                  {structure.ptm != null && <span>pTM {structure.ptm.toFixed(2)}</span>}
                  {structure.iptm != null && <span>ipTM {structure.iptm.toFixed(2)}</span>}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section>
        <h3>Evidence</h3>
        <div className="evidence-strip">
          {Object.entries(design.evidence_counts).map(([kind, count]) => (
            <span key={kind}><b>{count}</b> {kind}</span>
          ))}
        </div>
        {design.evidence.length > 0 && (
          <div className="record-list">
            {design.evidence.map((entry) => (
              <article className="record-card" key={entry.id}>
                <div className="record-title">
                  <strong>{entry.source_name}</strong>
                  <span>{entry.source_type}</span>
                </div>
                <p>{entry.summary}</p>
              </article>
            ))}
          </div>
        )}
      </section>
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
      .then((response) => {
        if (!response.ok) throw new Error("Could not load projects.");
        return response.json();
      })
      .then((data: ProjectListItem[]) => {
        setProjects(data);
        if (data.length > 0) setSelectedSlug(data[0].slug);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedSlug) {
      setProject(null);
      return;
    }
    setLoading(true);
    setError(null);
    fetch(`/api/projects/${encodeURIComponent(selectedSlug)}`)
      .then((response) => {
        if (!response.ok) throw new Error("Could not load project archive.");
        return response.json();
      })
      .then((data: ProjectDetail) => {
        setProject(data);
        setSelectedDesignId(firstDesign(data.design_tree)?.id ?? null);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [selectedSlug]);

  const selectedDesign = useMemo(
    () => findDesign(project?.design_tree ?? [], selectedDesignId),
    [project, selectedDesignId],
  );

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Human-Guided Protein Design</p>
          <h1>Research workspace</h1>
        </div>
        <span className="version">v0.4 dev</span>
      </header>

      <div className="workspace">
        <aside className="sidebar">
          <div className="panel-title">
            <span>Projects</span>
            <span className="count">{projects.length}</span>
          </div>
          {projects.map((item) => (
            <button
              key={item.slug}
              className={`project-button ${selectedSlug === item.slug ? "active" : ""}`}
              onClick={() => setSelectedSlug(item.slug)}
            >
              <strong>{item.name}</strong>
              <span>{item.design_count} designs · {item.structure_count} structures</span>
            </button>
          ))}
          {!loading && projects.length === 0 && <p className="muted">No projects found in data/projects.</p>}
        </aside>

        <section className="canvas">
          {error && <div className="error-banner">{error}</div>}
          {loading && !project && <div className="empty-panel">Loading workspace…</div>}
          {project && (
            <>
              <div className="project-header">
                <div>
                  <p className="eyebrow">Project</p>
                  <h2>{project.name}</h2>
                </div>
                <div className="project-counts">
                  <span><b>{project.counts.designs}</b> designs</span>
                  <span><b>{project.counts.structures}</b> structures</span>
                  <span><b>{project.counts.evidence}</b> evidence</span>
                </div>
              </div>

              {project.objectives.length > 0 && (
                <div className="objective-card">
                  <span className="eyebrow">Scientific objective</span>
                  <p>{project.objectives[0].description}</p>
                  {project.objectives[0].constraints.length > 0 && (
                    <div className="chips">
                      {project.objectives[0].constraints.map((constraint) => <span key={constraint}>{constraint}</span>)}
                    </div>
                  )}
                </div>
              )}

              <div className="tree-panel">
                <div className="panel-title"><span>Design lineage</span></div>
                {project.design_tree.length === 0 ? (
                  <div className="empty-panel">This project has an objective but no designs yet.</div>
                ) : (
                  <ul className="tree-root">
                    {project.design_tree.map((node) => (
                      <TreeNode key={node.id} node={node} selectedId={selectedDesignId} onSelect={setSelectedDesignId} />
                    ))}
                  </ul>
                )}
              </div>
            </>
          )}
        </section>

        <aside className="inspector">
          <DesignInspector design={selectedDesign} />
        </aside>
      </div>
    </main>
  );
}
