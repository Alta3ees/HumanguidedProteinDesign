import { useEffect, useMemo, useRef, useState } from "react";
import { Stage } from "ngl";
import type { Component } from "ngl";
import type { StructureModel } from "./types";
import "./structure-viewer.css";

function localFileUrl(slug: string, path: string): string {
  return `/api/projects/${encodeURIComponent(slug)}/files/${path
    .split("/")
    .map((part) => encodeURIComponent(part))
    .join("/")}`;
}

function structureExtension(path: string): string {
  const filename = path.split("/").pop() ?? path;
  const extension = filename.includes(".") ? filename.split(".").pop()?.toLowerCase() ?? "" : "";
  if (extension === "mmcif") return "cif";
  if (extension === "ent") return "pdb";
  return extension || "pdb";
}

type RepresentationMode = "cartoon" | "surface" | "ball+stick";

export default function StructureViewer({
  slug,
  structures,
}: {
  slug: string;
  structures: StructureModel[];
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<Stage | null>(null);
  const componentRef = useRef<Component | null>(null);
  const [selectedId, setSelectedId] = useState(structures[0]?.id ?? "");
  const [representation, setRepresentation] = useState<RepresentationMode>("cartoon");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [loadedLabel, setLoadedLabel] = useState<string | null>(null);
  const [pymolBusy, setPymolBusy] = useState(false);
  const [pymolMessage, setPymolMessage] = useState<string | null>(null);

  const selected = useMemo(
    () => structures.find((structure) => structure.id === selectedId) ?? structures[0] ?? null,
    [structures, selectedId],
  );

  useEffect(() => {
    if (structures.length > 0 && !structures.some((structure) => structure.id === selectedId)) {
      setSelectedId(structures[0].id);
    }
  }, [structures, selectedId]);

  useEffect(() => {
    if (!hostRef.current) return;
    const stage = new Stage(hostRef.current, { backgroundColor: "white" });
    stageRef.current = stage;
    const resize = () => stage.handleResize();
    window.addEventListener("resize", resize);
    requestAnimationFrame(resize);
    return () => {
      window.removeEventListener("resize", resize);
      stage.dispose();
      stageRef.current = null;
      componentRef.current = null;
    };
  }, []);

  useEffect(() => {
    const stage = stageRef.current;
    if (!stage || !selected) return;
    const activeStage: Stage = stage;
    let cancelled = false;
    const controller = new AbortController();
    setLoading(true);
    setMessage(null);
    setLoadedLabel(null);
    activeStage.removeAllComponents();
    componentRef.current = null;

    async function loadStructure() {
      const path = selected.structure_path;
      const url = localFileUrl(slug, path);
      const extension = structureExtension(path);
      const response = await fetch(url, { signal: controller.signal });
      if (!response.ok) {
        let detail = `HTTP ${response.status}`;
        try {
          const payload = await response.json();
          if (payload?.detail) detail = String(payload.detail);
        } catch {
          // The endpoint may return a non-JSON error body.
        }
        throw new Error(`Could not read ${path}: ${detail}`);
      }
      const blob = await response.blob();
      if (blob.size === 0) throw new Error(`Structure file is empty: ${path}`);
      if (cancelled) return;
      const loaded = await activeStage.loadFile(blob, { ext: extension, defaultRepresentation: false });
      if (cancelled) return;
      if (!loaded) throw new Error("NGL parsed the file but did not return a structure component.");
      const component = loaded as Component;
      componentRef.current = component;
      component.addRepresentation(representation, {
        colorScheme: representation === "surface" ? "hydrophobicity" : "chainname",
      });
      if (representation !== "surface") {
        component.addRepresentation("ball+stick", { sele: "hetero and not water", colorScheme: "element" });
      }
      activeStage.handleResize();
      component.autoView();
      activeStage.autoView();
      requestAnimationFrame(() => activeStage.handleResize());
      const name = path.split("/").pop() ?? path;
      setLoadedLabel(`${name} · ${blob.size.toLocaleString()} bytes · ${extension.toUpperCase()}`);
    }

    loadStructure()
      .catch((error) => {
        if (!cancelled && error instanceof Error && error.name !== "AbortError") {
          setMessage(error.message || "Could not load structure.");
        }
      })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; controller.abort(); };
  }, [slug, selected, representation]);

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
      setPymolMessage("Opened in local PyMOL.");
    } catch (error) {
      setPymolMessage(error instanceof Error ? error.message : "Could not launch PyMOL.");
    } finally {
      setPymolBusy(false);
    }
  }

  if (structures.length === 0) return null;

  return (
    <section className="structure-viewer-panel">
      <div className="structure-viewer-toolbar">
        <div>
          <p className="eyebrow">Structure tools</p>
          <h3>Inspect structure</h3>
        </div>
        <div className="structure-viewer-controls">
          {structures.length > 1 && (
            <label>
              Structure
              <select value={selected?.id ?? ""} onChange={(event) => { setSelectedId(event.target.value); setPymolMessage(null); }}>
                {structures.map((structure, index) => (
                  <option key={structure.id} value={structure.id}>
                    {index + 1}. {structure.source}{structure.method ? ` · ${structure.method}` : ""}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label>
            Quick view
            <select value={representation} onChange={(event) => setRepresentation(event.target.value as RepresentationMode)}>
              <option value="cartoon">Cartoon</option>
              <option value="surface">Surface</option>
              <option value="ball+stick">Ball + stick</option>
            </select>
          </label>
          <button className="pymol-button" type="button" onClick={openInPyMOL} disabled={pymolBusy || !selected}>
            {pymolBusy ? "Opening…" : "Open in PyMOL ↗"}
          </button>
          {selected && (
            <a className="secondary-button structure-file-button" href={localFileUrl(slug, selected.structure_path)} target="_blank" rel="noreferrer">
              Raw file
            </a>
          )}
          {pymolMessage && <span className="pymol-message">{pymolMessage}</span>}
        </div>
      </div>

      <div className="structure-viewer-canvas-wrap">
        <div ref={hostRef} className="structure-viewer-canvas" />
        {loading && <div className="structure-viewer-status">Loading quick local preview…</div>}
        {message && <div className="structure-viewer-error">Quick preview: {message} — use “Open in PyMOL” for full inspection.</div>}
      </div>

      {selected && (
        <div className="structure-viewer-meta">
          <span className="mono">{selected.structure_path}</span>
          <span>{selected.source}</span>
          {loadedLabel && <span>{loadedLabel}</span>}
          {selected.mean_plddt != null && <span>pLDDT {selected.mean_plddt.toFixed(1)}</span>}
          {selected.ptm != null && <span>pTM {selected.ptm.toFixed(2)}</span>}
          {selected.iptm != null && <span>ipTM {selected.iptm.toFixed(2)}</span>}
        </div>
      )}
    </section>
  );
}
