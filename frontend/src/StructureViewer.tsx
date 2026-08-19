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

    let cancelled = false;
    setLoading(true);
    setMessage(null);
    stage.removeAllComponents();
    componentRef.current = null;

    stage
      .loadFile(localFileUrl(slug, selected.structure_path), { defaultRepresentation: false })
      .then((loaded) => {
        if (cancelled) return;
        if (!loaded) {
          throw new Error("NGL did not return a structure component.");
        }

        const component = loaded as Component;
        componentRef.current = component;
        component.addRepresentation(representation, {
          colorScheme: representation === "surface" ? "hydrophobicity" : "chainname",
        });
        if (representation !== "surface") {
          component.addRepresentation("ball+stick", {
            sele: "hetero and not water",
            colorScheme: "element",
          });
        }
        component.autoView();
      })
      .catch((error) => {
        if (!cancelled) {
          setMessage(error instanceof Error ? error.message : "Could not load structure.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [slug, selected, representation]);

  if (structures.length === 0) return null;

  return (
    <section className="structure-viewer-panel">
      <div className="structure-viewer-toolbar">
        <div>
          <p className="eyebrow">Local 3D viewer</p>
          <h3>Structure visualization</h3>
        </div>
        <div className="structure-viewer-controls">
          {structures.length > 1 && (
            <label>
              Model
              <select value={selected?.id ?? ""} onChange={(event) => setSelectedId(event.target.value)}>
                {structures.map((structure, index) => (
                  <option key={structure.id} value={structure.id}>
                    {index + 1}. {structure.source}{structure.method ? ` · ${structure.method}` : ""}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label>
            View
            <select
              value={representation}
              onChange={(event) => setRepresentation(event.target.value as RepresentationMode)}
            >
              <option value="cartoon">Cartoon</option>
              <option value="surface">Surface</option>
              <option value="ball+stick">Ball + stick</option>
            </select>
          </label>
          {selected && (
            <a
              className="secondary-button structure-file-button"
              href={localFileUrl(slug, selected.structure_path)}
              target="_blank"
              rel="noreferrer"
            >
              Open raw file ↗
            </a>
          )}
        </div>
      </div>

      <div className="structure-viewer-canvas-wrap">
        <div ref={hostRef} className="structure-viewer-canvas" />
        {loading && <div className="structure-viewer-status">Loading local structure…</div>}
        {message && <div className="structure-viewer-error">{message}</div>}
      </div>

      {selected && (
        <div className="structure-viewer-meta">
          <span className="mono">{selected.structure_path}</span>
          <span>{selected.source}</span>
          {selected.mean_plddt != null && <span>pLDDT {selected.mean_plddt.toFixed(1)}</span>}
          {selected.ptm != null && <span>pTM {selected.ptm.toFixed(2)}</span>}
          {selected.iptm != null && <span>ipTM {selected.iptm.toFixed(2)}</span>}
        </div>
      )}
    </section>
  );
}
