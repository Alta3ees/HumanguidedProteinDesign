import { useMemo, useState } from "react";
import type { ProjectDetail, StructureModel } from "./types";
import "./structure-viewer.css";

function localFileUrl(slug: string, path: string): string {
  return `/api/projects/${encodeURIComponent(slug)}/files/${path
    .split("/")
    .map((part) => encodeURIComponent(part))
    .join("/")}`;
}

export default function StructureViewer({
  slug,
  structures,
  onUpdated,
}: {
  slug: string;
  structures: StructureModel[];
  onUpdated: (project: ProjectDetail) => void;
}) {
  const [selectedId, setSelectedId] = useState(structures[0]?.id ?? "");
  const [pymolBusy, setPymolBusy] = useState(false);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [pymolMessage, setPymolMessage] = useState<string | null>(null);

  const selected = useMemo(
    () => structures.find((structure) => structure.id === selectedId) ?? structures[0] ?? null,
    [structures, selectedId],
  );

  async function openInPyMOL() {
    if (!selected) return;
    setPymolBusy(true);
    setPymolMessage(null);
    try {
      const response = await fetch(`/api/projects/${encodeURIComponent(slug)}/launch-pymol`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ relative_path: selected.structure_path }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail ?? "Could not launch PyMOL.");

      if (payload.status === "running") {
        setPymolMessage("PyMOL is running with this structure.");
      } else {
        setPymolMessage(`PyMOL launcher returned. Check ${payload.log ?? ".hgd/pymol-launch.log"} if no window appeared.`);
      }
    } catch (error) {
      setPymolMessage(error instanceof Error ? error.message : "Could not launch PyMOL.");
    } finally {
      setPymolBusy(false);
    }
  }

  async function deleteSelectedStructure() {
    if (!selected) return;
    const filename = selected.structure_path.split("/").pop() ?? selected.structure_path;
    if (!window.confirm(`Delete structure "${filename}" from this design?\n\nThe project-local structure file will also be deleted. Historical evidence will be kept, but marked as referring to a removed structure.`)) return;

    setDeleteBusy(true);
    setPymolMessage(null);
    try {
      const response = await fetch(
        `/api/projects/${encodeURIComponent(slug)}/structures/${encodeURIComponent(selected.id)}`,
        { method: "DELETE" },
      );
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail ?? "Could not delete structure.");
      const remaining = structures.filter((structure) => structure.id !== selected.id);
      setSelectedId(remaining[0]?.id ?? "");
      onUpdated(payload.project as ProjectDetail);
    } catch (error) {
      setPymolMessage(error instanceof Error ? error.message : "Could not delete structure.");
    } finally {
      setDeleteBusy(false);
    }
  }

  if (!selected) return null;

  const filename = selected.structure_path.split("/").pop() ?? selected.structure_path;

  return (
    <section className="structure-viewer-panel compact-structure-tools">
      <div className="structure-viewer-toolbar">
        <div className="structure-tool-title">
          <p className="eyebrow">Structure tools</p>
          <h3>{filename}</h3>
          <span className="muted">{selected.source}{selected.method ? ` · ${selected.method}` : ""}</span>
        </div>

        <div className="structure-viewer-controls">
          {structures.length > 1 && (
            <label>
              Structure
              <select
                value={selected.id}
                onChange={(event) => {
                  setSelectedId(event.target.value);
                  setPymolMessage(null);
                }}
              >
                {structures.map((structure, index) => (
                  <option key={structure.id} value={structure.id}>
                    {index + 1}. {structure.source}{structure.method ? ` · ${structure.method}` : ""}
                  </option>
                ))}
              </select>
            </label>
          )}

          <button className="pymol-button" type="button" onClick={openInPyMOL} disabled={pymolBusy || deleteBusy}>
            {pymolBusy ? "Opening…" : "Open in PyMOL ↗"}
          </button>

          <a
            className="secondary-button structure-file-button"
            href={localFileUrl(slug, selected.structure_path)}
            target="_blank"
            rel="noreferrer"
          >
            Raw file
          </a>

          <button
            className="danger-button structure-delete-button"
            type="button"
            onClick={deleteSelectedStructure}
            disabled={deleteBusy || pymolBusy}
          >
            {deleteBusy ? "Deleting…" : "Delete structure"}
          </button>
        </div>
      </div>

      <div className="compact-structure-meta">
        <span className="mono">{selected.structure_path}</span>
        {selected.mean_plddt != null && <span>pLDDT {selected.mean_plddt.toFixed(1)}</span>}
        {selected.ptm != null && <span>pTM {selected.ptm.toFixed(2)}</span>}
        {selected.iptm != null && <span>ipTM {selected.iptm.toFixed(2)}</span>}
      </div>

      {pymolMessage && <div className="pymol-message pymol-message-block">{pymolMessage}</div>}
    </section>
  );
}
