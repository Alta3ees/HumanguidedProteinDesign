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
};

function scoreSnapshot(design: DesignNode): ScoreSnapshot | null {
  const entries = [...design.evidence].reverse();
  for (const evidence of entries) {
    if (evidence.source_type !== "computational" || !evidence.data) continue;
    const data = evidence.data;
    if (typeof data.mutant_score === "number") {
      return {
        design,
        evidence,
        score: data.mutant_score,
        scoreKind: "mutation evaluation",
        terms: (data.mutant_score_terms ?? data.score_terms ?? {}) as Record<string, number>,
        mutation: typeof data.mutation === "string" ? data.mutation : null,
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
      };
    }
  }
  return null;
}

function sequenceDifferences(a: DesignNode, b: DesignNode): string[] {
  if (!a.sequence || !b.sequence || a.sequence.length !== b.sequence.length) return [];
  const differences: string[] = [];
  for (let index = 0; index < a.sequence.length; index += 1) {
    if (a.sequence[index] !== b.sequence[index]) {
      differences.push(`${a.sequence[index]}${index + 1}${b.sequence[index]}`);
    }
  }
  return differences;
}

function signed(value: number, digits = 3) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(digits)}`;
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
  }, [designAId, designBId, eligibleIds, firstEligible, fallbackB]);

  const a = eligible.find((item) => item.design.id === designAId) ?? null;
  const b = eligible.find((item) => item.design.id === designBId) ?? null;
  const differences = a && b ? sequenceDifferences(a.design, b.design) : [];
  const termNames = a && b
    ? Array.from(new Set([...Object.keys(a.terms), ...Object.keys(b.terms)]))
      .filter((term) => term !== "total_score" && typeof a.terms[term] === "number" && typeof b.terms[term] === "number")
    : [];

  return <section className="comparison-card">
    <div className="comparison-heading">
      <div>
        <p className="eyebrow">Archived PyRosetta comparison</p>
        <h3>Compare Design A vs Design B</h3>
        <p>This compares two existing designs using a PyRosetta score already archived on each design. HGD never silently substitutes WT as the reference.</p>
      </div>
      <span>{eligible.length} scored design{eligible.length === 1 ? "" : "s"}</span>
    </div>

    {eligible.length < 2 ? <div className="comparison-empty">
      <b>Two scored designs are required.</b>
      <span>Mutation-generated designs receive their own PyRosetta score automatically. For another design, open its full scientific record and use “Score current structure”.</span>
    </div> : <>
      <div className="comparison-selectors">
        <label><span>Design A · reference</span><select value={designAId} onChange={(event) => setDesignAId(event.target.value)}>{eligible.map((item) => <option key={item.design.id} value={item.design.id}>{item.design.label}</option>)}</select><small>The comparison is calculated relative to this selected design — not WT unless you explicitly choose WT here.</small></label>
        <div className="comparison-vs">VS</div>
        <label><span>Design B · comparison</span><select value={designBId} onChange={(event) => setDesignBId(event.target.value)}>{eligible.map((item) => <option key={item.design.id} value={item.design.id} disabled={item.design.id === designAId}>{item.design.label}</option>)}</select><small>HGD reports Score(B) − Score(A). A negative value means B has the lower archived Rosetta score.</small></label>
      </div>

      {a && b && a.design.id !== b.design.id && <div className="comparison-result">
        <div className="comparison-equation">
          <div><span>Design A</span><strong>{a.design.label}</strong><b>{a.score.toFixed(3)} REU</b></div>
          <span>→</span>
          <div><span>Design B</span><strong>{b.design.label}</strong><b>{b.score.toFixed(3)} REU</b></div>
          <div className="comparison-delta"><span>B − A</span><strong className={b.score - a.score <= 0 ? "score-good" : "score-bad"}>{signed(b.score - a.score)} REU</strong></div>
        </div>

        <div className="comparison-source-grid">
          <article><b>A score source</b><span>{a.evidence.source_name} · {a.scoreKind}</span><small>{a.mutation ? `${a.mutation} · ` : ""}{a.evidence.created_at.slice(0, 10)}</small></article>
          <article><b>B score source</b><span>{b.evidence.source_name} · {b.scoreKind}</span><small>{b.mutation ? `${b.mutation} · ` : ""}{b.evidence.created_at.slice(0, 10)}</small></article>
        </div>

        <div className="comparison-note"><b>Interpretation</b><span>This is an explicit comparison of the two archived design scores shown above. It is not the mutation ΔScore against a hidden WT reference. Independently prepared structures may still represent different local minima, so interpret absolute-score comparisons with the archived protocol context.</span></div>

        {a.design.sequence && b.design.sequence && <div className="comparison-sequence"><b>Sequence difference A → B</b>{a.design.sequence.length !== b.design.sequence.length ? <span>Sequences have different lengths ({a.design.sequence.length} vs {b.design.sequence.length} aa).</span> : differences.length ? <div>{differences.map((mutation) => <code key={mutation}>{mutation}</code>)}</div> : <span>Sequences are identical.</span>}</div>}

        {termNames.length > 0 && <div className="energy-table-wrap"><table className="energy-table"><thead><tr><th>Rosetta term</th><th>{a.design.label}</th><th>{b.design.label}</th><th>B − A</th></tr></thead><tbody>{termNames.map((term) => { const delta = b.terms[term] - a.terms[term]; return <tr key={term}><td className="mono">{term}</td><td>{a.terms[term].toFixed(3)}</td><td>{b.terms[term].toFixed(3)}</td><td className={delta <= 0 ? "score-good" : "score-bad"}>{signed(delta)}</td></tr>; })}</tbody></table></div>}
      </div>}
    </>}
  </section>;
}
