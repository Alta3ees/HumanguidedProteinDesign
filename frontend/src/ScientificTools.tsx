import { FormEvent, useMemo, useState } from "react";
import type { DesignNode, ProjectDetail } from "./types";

type ScanRow = {
  mutation: string;
  position: number;
  wt_aa: string;
  mutant_aa: string;
  total_score: number;
  delta_score: number;
  [key: string]: string | number;
};

type Evaluation = {
  mutation: string;
  position: number;
  wt_aa: string;
  mutant_aa: string;
  previous_score: number;
  mutant_score: number;
  delta_score: number;
  delta_score_terms?: Record<string, number>;
};

type StructureScore = {
  total_score: number;
  residue_count: number;
  structure_file: string;
  score_terms: Record<string, number>;
  design_sequence_length?: number | null;
  structure_sequence_length?: number;
  sequence_match?: boolean;
  sequence_warning?: string | null;
};

const AMINO_ACIDS = [
  ["A", "Alanine"], ["C", "Cysteine"], ["D", "Aspartate"], ["E", "Glutamate"],
  ["F", "Phenylalanine"], ["G", "Glycine"], ["H", "Histidine"], ["I", "Isoleucine"],
  ["K", "Lysine"], ["L", "Leucine"], ["M", "Methionine"], ["N", "Asparagine"],
  ["P", "Proline"], ["Q", "Glutamine"], ["R", "Arginine"], ["S", "Serine"],
  ["T", "Threonine"], ["V", "Valine"], ["W", "Tryptophan"], ["Y", "Tyrosine"],
] as const;

async function responseJson(response: Response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail ?? "Request failed.");
  return payload;
}

function localFileUrl(slug: string, path: string) {
  return `/api/projects/${encodeURIComponent(slug)}/files/${path.split("/").map(encodeURIComponent).join("/")}`;
}

function scoreCell(row: ScanRow, term: string) {
  const value = row[term];
  return typeof value === "number" ? value.toFixed(3) : "—";
}

export function PyRosettaWorkbench({ slug, design, onUpdated, onSelectNew }: {
  slug: string;
  design: DesignNode;
  onUpdated: (project: ProjectDetail) => void;
  onSelectNew: (id: string) => void;
}) {
  const [position, setPosition] = useState("1");
  const [radius, setRadius] = useState("8");
  const [mutantAa, setMutantAa] = useState("A");
  const [hypothesis, setHypothesis] = useState("");
  const [objective, setObjective] = useState("");
  const [designName, setDesignName] = useState("");
  const [scanBusy, setScanBusy] = useState(false);
  const [mutationBusy, setMutationBusy] = useState(false);
  const [scoreBusy, setScoreBusy] = useState(false);
  const [structureScore, setStructureScore] = useState<StructureScore | null>(null);
  const [scanRows, setScanRows] = useState<ScanRow[]>([]);
  const [scanPath, setScanPath] = useState<string | null>(null);
  const [candidateId, setCandidateId] = useState<string | null>(null);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [rationale, setRationale] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const hasStructure = design.structures.length > 0 || Boolean(design.structure_path);
  const maxPosition = design.sequence?.length ?? undefined;
  const numericPosition = Number(position);
  const currentResidue = useMemo(() => {
    if (!design.sequence || !Number.isInteger(numericPosition) || numericPosition < 1 || numericPosition > design.sequence.length) return null;
    return design.sequence[numericPosition - 1];
  }, [design.sequence, numericPosition]);

  async function scoreStructure() {
    setScoreBusy(true); setMessage(null); setStructureScore(null);
    try {
      const payload = await responseJson(await fetch(`/api/projects/${encodeURIComponent(slug)}/designs/${encodeURIComponent(design.id)}/score-structure`, { method: "POST" }));
      const data = (payload.evidence?.data ?? {}) as StructureScore;
      setStructureScore(data);
      onUpdated(payload.project as ProjectDetail);
      setMessage("Current structure score archived as computational evidence.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Structure scoring failed.");
    } finally { setScoreBusy(false); }
  }

  function useScanCandidate(row: ScanRow) {
    setPosition(String(row.position));
    setMutantAa(row.mutant_aa);
    setEvaluation(null);
    setCandidateId(null);
    setMessage(`Loaded ${row.mutation} into the point-mutation evaluator.`);
  }

  async function runScan(event: FormEvent) {
    event.preventDefault();
    setScanBusy(true); setMessage(null); setScanRows([]); setScanPath(null);
    try {
      const payload = await responseJson(await fetch(`/api/projects/${encodeURIComponent(slug)}/designs/${encodeURIComponent(design.id)}/position-scan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ position: Number(position), radius: Number(radius) }),
      }));
      setScanRows(payload.results as ScanRow[]);
      setScanPath(payload.file_path as string);
      onUpdated(payload.project as ProjectDetail);
      setMessage("Position scan archived as computational evidence.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Position scan failed.");
    } finally { setScanBusy(false); }
  }

  async function evaluateMutation(event: FormEvent) {
    event.preventDefault();
    if (currentResidue === mutantAa) {
      setMessage(`Position ${position} is already ${mutantAa}. Choose a different amino acid.`);
      return;
    }
    setMutationBusy(true); setMessage(null); setEvaluation(null); setCandidateId(null);
    try {
      const payload = await responseJson(await fetch(`/api/projects/${encodeURIComponent(slug)}/designs/${encodeURIComponent(design.id)}/evaluate-mutation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          position: Number(position), mutant_aa: mutantAa, radius: Number(radius),
          hypothesis, objective, design_name: designName || null,
        }),
      }));
      const newId = payload.candidate_design_id as string;
      setCandidateId(newId);
      setEvaluation(payload.evaluation as Evaluation);
      onUpdated(payload.project as ProjectDetail);
      setMessage("New child design created in the design map automatically. Inspect the score below, then Accept, Defer, or Reject it.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Mutation evaluation failed.");
    } finally { setMutationBusy(false); }
  }

  async function decide(outcome: "accepted" | "rejected" | "deferred") {
    if (!candidateId) return;
    setMutationBusy(true); setMessage(null);
    try {
      const payload = await responseJson(await fetch(`/api/projects/${encodeURIComponent(slug)}/designs/${encodeURIComponent(candidateId)}/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ outcome, rationale }),
      }));
      onUpdated(payload.project as ProjectDetail);
      onSelectNew(candidateId);
      setMessage(`${evaluation?.mutation ?? "Candidate"} recorded as ${outcome}. Its child node is now selected in the design map.`);
      setCandidateId(null); setEvaluation(null); setRationale("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not record decision.");
    } finally { setMutationBusy(false); }
  }

  const scoreTerms = structureScore?.score_terms ? Object.entries(structureScore.score_terms) : [];

  return <section className="detail-card wide-section scientific-workbench">
    <div className="detail-card-header workbench-title"><div><p className="eyebrow">PyRosetta design tools</p><h3>Mutation workbench</h3><p className="workbench-intro">Use a structure-backed design to score the current model, test one hypothesis-driven substitution, or screen every amino acid at a position. Every calculation is retained in the project archive.</p></div><span>local repack + minimization · {radius || "8"} Å</span></div>
    {!hasStructure && <p className="form-error">Attach a structure to this design before running PyRosetta.</p>}

    <div className="baseline-score-bar"><div><p className="eyebrow">1 · Baseline structure</p><b>Score the currently attached structure</b><p>Useful before mutations: establishes the Rosetta energy of the model you are actually evaluating. This does not modify the design.</p></div><button className="secondary-button" type="button" disabled={!hasStructure || scoreBusy} onClick={scoreStructure}>{scoreBusy ? "Scoring…" : "Score current structure"}</button></div>
    {structureScore && <div className="baseline-score-result"><div className="score-grid"><div><span>Total score</span><b>{structureScore.total_score.toFixed(2)} REU</b></div><div><span>Structure residues</span><b>{structureScore.residue_count}</b></div><div><span>Structure</span><b className="mono">{structureScore.structure_file}</b></div></div>{structureScore.sequence_warning && <div className="compatibility-warning"><b>Structure does not match this design</b><p>{structureScore.sequence_warning}</p><span>Scoring is still valid for the structure itself, but mutation design is disabled until you attach the matching model.</span></div>}{scoreTerms.length > 0 && <div className="energy-table-wrap"><table className="energy-table"><thead><tr><th>Term</th><th>Weighted score</th></tr></thead><tbody>{scoreTerms.map(([term, value]) => <tr key={term}><td className="mono">{term}</td><td>{Number(value).toFixed(3)}</td></tr>)}</tbody></table></div>}</div>}

    <div className="workbench-grid">
      <form className="tool-card mutation-tool-card" onSubmit={evaluateMutation}>
        <div className="tool-card-heading"><p className="eyebrow">2 · Human-guided mutation</p><h4>Evaluate one substitution</h4><p>Use this when you already have a specific mutation in mind. HGD creates a child candidate, locally repacks/minimizes around the mutation, compares Rosetta energies, and waits for your Accept / Defer / Reject decision.</p></div>
        <div className="three-col-form guided-fields">
          <label>Position<input type="number" min="1" max={maxPosition} value={position} onChange={(e) => setPosition(e.target.value)} required /><small className="field-help">Residue number in this design{currentResidue ? ` · currently ${currentResidue}${position}` : ""}.</small></label>
          <label>Mutate to<select className="mono" value={mutantAa} onChange={(e) => setMutantAa(e.target.value)}>{AMINO_ACIDS.map(([code, name]) => <option key={code} value={code}>{code} — {name}</option>)}</select><small className="field-help">Choose the new amino acid. HGD rejects an unchanged residue.</small></label>
          <label>Local radius (Å)<input type="number" min="1" step="0.5" value={radius} onChange={(e) => setRadius(e.target.value)} /><small className="field-help">Residues within this distance can repack. 8 Å is the default local environment.</small></label>
        </div>
        <label>Hypothesis<textarea value={hypothesis} onChange={(e) => setHypothesis(e.target.value)} placeholder="Example: replacing Leu with Trp may improve hydrophobic packing in this core." /><small className="field-help">Write what you expect before seeing the score. This becomes part of provenance.</small></label>
        <label>Objective<textarea value={objective} onChange={(e) => setObjective(e.target.value)} placeholder="Example: improve local stability without disrupting the beta sheet." /><small className="field-help">The broader property or question you are trying to improve or test.</small></label>
        <label>Candidate name <span className="optional-label">optional</span><input value={designName} onChange={(e) => setDesignName(e.target.value)} placeholder={currentResidue ? `${currentResidue}${position}${mutantAa}` : "Short human-readable label"} /><small className="field-help">Only for readability in the design tree; the mutation is stored independently.</small></label>
        <div className="scan-explainer"><b>What happens after Evaluate</b><span>HGD creates a new child node automatically. The parent design is never overwritten.</span></div>
        <button className="primary-button" disabled={!hasStructure || mutationBusy}>{mutationBusy ? "Running PyRosetta…" : "Evaluate mutation"}</button>
        {evaluation && <div className="evaluation-result">
          <div className="score-grid"><div><span>Mutation</span><b className="mono">{evaluation.mutation}</b></div><div><span>Parent</span><b>{evaluation.previous_score.toFixed(2)}</b></div><div><span>Mutant</span><b>{evaluation.mutant_score.toFixed(2)}</b></div><div><span>ΔScore</span><b className={evaluation.delta_score <= 0 ? "score-good" : "score-bad"}>{evaluation.delta_score >= 0 ? "+" : ""}{evaluation.delta_score.toFixed(2)} REU</b></div></div>
          <label>Decision rationale<textarea value={rationale} onChange={(e) => setRationale(e.target.value)} placeholder="Explain why this evidence is sufficient to accept, reject, or defer the candidate." /></label>
          <div className="decision-actions"><button type="button" className="primary-button" onClick={() => decide("accepted")}>Accept</button><button type="button" className="secondary-button" onClick={() => decide("deferred")}>Defer</button><button type="button" className="danger-button" onClick={() => decide("rejected")}>Reject</button></div>
        </div>}
      </form>

      <form className="tool-card scan-tool-card" onSubmit={runScan}>
        <div className="tool-card-heading"><p className="eyebrow">3 · Systematic position scan</p><h4>Try every amino acid here</h4><p>Use this when you know <em>where</em> you want to explore but not <em>which amino acid</em> to choose. HGD tests all 19 non-WT substitutions under the same local protocol and ranks them by ΔScore.</p></div>
        <div className="two-col-form guided-fields"><label>Position<input type="number" min="1" max={maxPosition} value={position} onChange={(e) => setPosition(e.target.value)} required /><small className="field-help">The single site to saturate{currentResidue ? ` · WT residue ${currentResidue}${position}` : ""}.</small></label><label>Local radius (Å)<input type="number" min="1" step="0.5" value={radius} onChange={(e) => setRadius(e.target.value)} /><small className="field-help">Use the same radius when comparing scans between positions.</small></label></div>
        <div className="scan-explainer"><b>How to read the result</b><span>More negative ΔScore = Rosetta prefers that substitution relative to the locally prepared WT reference. Treat it as evidence, not an automatic design decision.</span></div>
        <button className="secondary-button" disabled={!hasStructure || scanBusy}>{scanBusy ? "Scanning 19 substitutions…" : "Scan all substitutions"}</button>
        {scanRows.length > 0 && <div className="scan-results"><div className="scan-result-header"><b>{scanRows.length} substitutions ranked by ΔScore</b>{scanPath && <a className="mono" href={localFileUrl(slug, scanPath)} target="_blank" rel="noreferrer">Complete CSV ↗</a>}</div><div className="energy-table-wrap"><table className="energy-table"><thead><tr><th>Rank</th><th>Mutation</th><th>Total</th><th>ΔScore</th><th>fa_atr</th><th>fa_rep</th><th>fa_sol</th><th>fa_elec</th><th /></tr></thead><tbody>{scanRows.map((row, index) => <tr key={row.mutation}><td>{index + 1}</td><td className="mono">{row.mutation}</td><td>{Number(row.total_score).toFixed(3)}</td><td className={Number(row.delta_score) <= 0 ? "score-good" : "score-bad"}>{Number(row.delta_score) >= 0 ? "+" : ""}{Number(row.delta_score).toFixed(3)}</td><td>{scoreCell(row, "fa_atr")}</td><td>{scoreCell(row, "fa_rep")}</td><td>{scoreCell(row, "fa_sol")}</td><td>{scoreCell(row, "fa_elec")}</td><td><button type="button" className="mini-button" onClick={() => useScanCandidate(row)}>Evaluate</button></td></tr>)}</tbody></table></div></div>}
      </form>
    </div>
    {message && <p className="form-message workbench-message">{message}</p>}
  </section>;
}

// The old standalone decision form is intentionally gone. Keep this no-op
// export temporarily so older workspace code can render it without creating a
// second decision UI; decisions are made directly after mutation evaluation.
export function DecisionRecorder(_props: {
  slug: string;
  design: DesignNode;
  onUpdated: (project: ProjectDetail) => void;
}) {
  return null;
}

export function ProjectExportTools({ slug }: { slug: string }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [contextPath, setContextPath] = useState<string | null>(null);

  async function exportContext() {
    setBusy(true); setMessage(null);
    try {
      const payload = await responseJson(await fetch(`/api/projects/${encodeURIComponent(slug)}/export/context`, { method: "POST" }));
      const path = payload.file_path as string;
      setContextPath(path);
      setMessage("LLM-ready project context updated from the current archive.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Context export failed.");
    } finally { setBusy(false); }
  }

  return <div className="project-export-tools">
    <button className="secondary-button" onClick={exportContext} disabled={busy}>{busy ? "Exporting…" : "Export context for LLM (.md)"}</button>
    {contextPath && <a className="mini-button" href={localFileUrl(slug, contextPath)} target="_blank" rel="noreferrer">Open Markdown ↗</a>}
    {message && <span className="tool-inline-message">{message}</span>}
  </div>;
}
