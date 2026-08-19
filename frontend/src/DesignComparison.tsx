import { useEffect, useMemo, useState } from "react";
import type { DesignNode, EvidenceEntry } from "./types";
import "./comparison.css";

type ScoreSnapshot = {
  design: DesignNode;
  evidence: EvidenceEntry;
  score: number;
  scoreKind: "mutation evaluation" | "structure score";
  terms: Record<string, number>;
  mutation: string | null;
  radius: number | null;
  residueCount: number | null;
};

function scoreSnapshot(design: DesignNode): ScoreSnapshot | null {
  const entries = [...design.evidence].reverse();
  for (const evidence of entries) {
    if (evidence.source_type !== "computational" || !evidence.data) continue;
    const data = evidence.data;
    if (typeof data.mutant_score === "number") {
      const preparation = (data.preparation ?? {}) as Record<string, unknown>;
      const context = (data.context ?? {}) as Record<string, unknown>;
      const radius = typeof preparation.radius_angstrom === "number"
        ? preparation.radius_angstrom
        : typeof context.radius_angstrom === "number"
          ? context.radius_angstrom
          : null;
      return {
        design,
        evidence,
        score: data.mutant_score,
        scoreKind: "mutation evaluation",
        terms: (data.mutant_score_terms ?? data.score_terms ?? {}) as Record<string, number>,
        mutation: typeof data.mutation === "string" ? data.mutation : null,
        radius,
        residueCount: design.sequence?.length ?? null,
      };
    }
    if (data.analysis_type === "structure_score" && typeof data.total_score === "number") {
      return {
        design,
        evidence,
        score: data.total_score,
        scoreKind: "structure score",
        terms: (data.score_terms ?? {}) as Record<string, number>,
        mutation: null,
        radius: null,
        residueCount: typeof data.residue_count === "number" ? data.residue_count : design.sequence?.length ?? null,
      };
    }
  }
  return null;
}

function sequenceDifferences(a: DesignNode, b: DesignNode): string[] {
  if (!a.sequence || !b.sequence || a.sequence.length !== b.sequence.length) return [];
  const differences: string[] = [];
  for (let index = 0; index < a.sequence.length; index += 1) {
    if (a.sequence[index] !== b.sequence[index]) differences.push(`${a.sequence[index]}${index + 1}${b.sequence[index]}`);
  }
  return differences;
}

function signed(value: number, digits = 3) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(digits)}`;
}

function comparisonIssues(a: ScoreSnapshot, b: ScoreSnapshot): string[] {
  const issues: string[] = [];
  if (a.scoreKind !== b.scoreKind) {
    issues.push(`A uses a ${a.scoreKind}, while B uses a ${b.scoreKind}. HGD will not subtract scores produced by different workflows.`);
  }
  if (a.residueCount != null && b.residueCount != null && a.residueCount !== b.residueCount) {
    issues.push(`The scored models have different residue counts (${a.residueCount} vs ${b.residueCount}). Absolute Rosetta scores scale with system size.`);
  }
  if (a.scoreKind === "mutation evaluation" && b.scoreKind === "mutation evaluation" && a.radius != null && b.radius != null && a.radius !== b.radius) {
    issues.push(`The mutation evaluations used different local preparation radii (${a.radius} Å vs ${b.radius} Å).`);
  }
  return issues;
}

export default function DesignComparison({ designs, selectedDesignId }: {
  designs: DesignNode[];
  selectedDesignId: string | null;
}) {
  const eligible = useMemo(
    () => designs.map((design) => scoreSnapshot(design)).filter((item): item is ScoreSnapshot => item !== null),
    [designs],
  );
  const eligibleIds = useMemo(() => new Set(eligible.map((item) => item.design.id)), [eligible]);
  const firstEligible = eligible[0]?.design.id ?? "";
  const selectedEligible = selectedDesignId && eligibleIds.has(selectedDesignId) ? selectedDesignId : firstEligible;
  const fallbackB = eligible.find((item) => item.design.id !== selectedEligible)?.design.id ?? "";
  const [designAId, setDesignAId] = useState(selectedEligible);
  const [designBId, setDesignBId] = useState(fallbackB);

  useEffect(() => {
    if (selectedDesignId && eligibleIds.has(selectedDesignId)) {
      setDesignAId(selectedDesignId);
      setDesignBId((current) => current && current !== selectedDesignId ? current : (eligible.find((item) => item.design.id !== selectedDesignId)?.design.id ?? ""));
    }
  }, [selectedDesignId, eligibleIds, eligible]);

  useEffect(() => {
    if (designAId && !eligibleIds.has(designAId)) setDesignAId(firstEligible);
    if (designBId && !eligibleIds.has(designBId)) setDesignBId(fallbackB);
    if (designAId && designBId && designAId === designBId) {
      setDesignBId(eligible.find((item) => item.design.id !== designAId)?.design.id ?? "");
    }
  }, [designAId, designBId, eligibleIds, eligible, firstEligible, fallbackB]);

  const a = eligible.find((item) => item.design.id === designAId) ?? null;
  const b = eligible.find((item) => item.design.id === designBId) ?? null;
  const differences = a && b ? sequenceDifferences(a.design, b.design) : [];
  const issues = a && b ? comparisonIssues(a, b) : [];
  const comparable = Boolean(a && b && issues.length === 0);
  const delta = a && b ? b.score - a.score : null;
  const termNames = comparable && a && b
    ? Array.from(new Set([...Object.keys(a.terms), ...Object.keys(b.terms)]))
      .filter((term) => term !== "total_score" && typeof a.terms[term] === "number" && typeof b.terms[term] === "number")
    : [];

  return <section className="comparison-card">
    <div className="comparison-heading">
      <div>
        <p className="eyebrow">Archived PyRosetta comparison</p>
        <h3>Compare Design A vs Design B</h3>
        <p>Choose two existing scored designs deliberately. This is a directional numerical comparison of archived Rosetta scores, not a new mutation experiment and not an automatic comparison to WT.</p>
      </div>
      <span>{eligible.length} scored design{eligible.length === 1 ? "" : "s"}</span>
    </div>

    {eligible.length < 2 ? <div className="comparison-empty">
      <b>Two scored designs are required.</b>
      <span>Mutation-generated designs receive their own PyRosetta score automatically. For another design, open its full scientific record and use “Score current structure”.</span>
    </div> : <>
      <div className="comparison-selectors">
        <label><span>Design A · reference</span><select value={designAId} onChange={(event) => setDesignAId(event.target.value)}>{eligible.map((item) => <option key={item.design.id} value={item.design.id}>{item.design.label} · {item.score.toFixed(2)} REU</option>)}</select><small>A is simply the mathematical reference for this view. It is not automatically WT.</small></label>
        <div className="comparison-vs">VS</div>
        <label><span>Design B · comparison</span><select value={designBId} onChange={(event) => setDesignBId(event.target.value)}>{eligible.map((item) => <option key={item.design.id} value={item.design.id} disabled={item.design.id === designAId}>{item.design.label} · {item.score.toFixed(2)} REU</option>)}</select><small>The displayed difference is always Score(B) − Score(A). Swapping A and B must reverse its sign.</small></label>
      </div>

      {a && b && a.design.id !== b.design.id && <div className="comparison-result">
        <div className="comparison-equation">
          <div><span>Design A</span><strong>{a.design.label}</strong><b>{a.score.toFixed(3)} REU</b></div>
          <span>→</span>
          <div><span>Design B</span><strong>{b.design.label}</strong><b>{b.score.toFixed(3)} REU</b></div>
          <div className="comparison-delta"><span>B − A</span><strong>{comparable && delta != null ? `${signed(delta)} REU` : "not comparable"}</strong></div>
        </div>

        <div className="comparison-source-grid">
          <article><b>A score source</b><span>{a.evidence.source_name} · {a.scoreKind}</span><small>{a.mutation ? `${a.mutation} · ` : ""}{a.evidence.created_at.slice(0, 10)}{a.radius != null ? ` · ${a.radius} Å` : ""}</small></article>
          <article><b>B score source</b><span>{b.evidence.source_name} · {b.scoreKind}</span><small>{b.mutation ? `${b.mutation} · ` : ""}{b.evidence.created_at.slice(0, 10)}{b.radius != null ? ` · ${b.radius} Å` : ""}</small></article>
        </div>

        {issues.length > 0 ? <div className="compatibility-warning"><b>Do not interpret this pair numerically</b>{issues.map((issue) => <p key={issue}>{issue}</p>)}</div> : delta != null && <div className="comparison-note"><b>How to read the sign</b><span>{delta < 0 ? `B's archived score is ${Math.abs(delta).toFixed(3)} REU lower than A's.` : delta > 0 ? `B's archived score is ${Math.abs(delta).toFixed(3)} REU higher than A's.` : "A and B have the same archived score."} Lower is not an intrinsic label of “better”: it is meaningful only when the scored systems and preparation protocol are genuinely comparable. If you swap A and B, the sign reverses by definition.</span></div>}

        <div className="comparison-note"><b>Scientific caution</b><span>A surprisingly large difference such as thousands of REU is a reason to inspect the structures, residue counts, and score provenance — not evidence of an extraordinarily favorable mutation. Use this tool for logically related designs evaluated under the same protocol.</span></div>

        {a.design.sequence && b.design.sequence && <div className="comparison-sequence"><b>Sequence difference A → B</b>{a.design.sequence.length !== b.design.sequence.length ? <span>Sequences have different lengths ({a.design.sequence.length} vs {b.design.sequence.length} aa).</span> : differences.length ? <div>{differences.map((mutation) => <code key={mutation}>{mutation}</code>)}</div> : <span>Sequences are identical.</span>}</div>}

        {termNames.length > 0 && <div className="energy-table-wrap"><table className="energy-table"><thead><tr><th>Rosetta term</th><th>{a.design.label}</th><th>{b.design.label}</th><th>B − A</th></tr></thead><tbody>{termNames.map((term) => { const termDelta = b.terms[term] - a.terms[term]; return <tr key={term}><td className="mono">{term}</td><td>{a.terms[term].toFixed(3)}</td><td>{b.terms[term].toFixed(3)}</td><td>{signed(termDelta)}</td></tr>; })}</tbody></table></div>}
      </div>}
    </>}
  </section>;
}
