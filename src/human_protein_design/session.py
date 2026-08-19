"""Human-guided protein design session utilities."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from pyrosetta.rosetta.core.pose import Pose

from human_protein_design.analysis import MutationAnalysis, analyze_mutation
from human_protein_design.archive import Decision, Design, DesignArchive, EvidenceEntry
from human_protein_design.context import MutationContext, get_mutation_context
from human_protein_design.interpretation import interpret_energy_changes
from human_protein_design.mutation import mutate_pose
from human_protein_design.scan import prepare_pose


@dataclass
class MutationResult:
    """Result of one proposed mutation."""

    mutation: str
    position: int
    wt_aa: str
    mutant_aa: str
    previous_score: float
    mutant_score: float
    delta_score: float
    scores: dict[str, float]


@dataclass
class DesignSession:
    """Store the state of a human-guided design session."""

    pose: Pose
    score_function: object
    archive: DesignArchive
    radius: float = 8.0
    output_dir: str | Path | None = None
    archive_path: str | Path | None = None
    structures_dir: str | Path | None = None
    history: list[MutationResult] = field(default_factory=list)
    current_design_id: str | None = None
    pending_design_id: str | None = None
    pending_evidence_id: str | None = None

    def __post_init__(self) -> None:
        """Initialize session storage and resolve current design."""
        if self.output_dir is not None:
            self.output_dir = Path(self.output_dir)
            self.output_dir.mkdir(parents=True, exist_ok=True)

        if self.current_design_id is not None:
            if self.current_design_id not in self.archive.designs:
                raise ValueError(f"Unknown current design: {self.current_design_id}")
            return

        if not self.archive.designs:
            root_design = Design(
                sequence=self.pose.sequence(),
                parent_design_id=None,
                status="active",
                name="WT",
                metadata={"role": "project_root"},
            )
            self._save_design_structure(root_design, self.pose, label="root")
            self.archive.add_design(root_design)
            self.current_design_id = root_design.id
            self._autosave_archive()
            return

        raise ValueError(
            "Archive already contains designs. Provide current_design_id when starting a new session."
        )

    def evaluate_mutation(
        self,
        position: int,
        mutant_aa: str,
        hypothesis: str = "",
        objective: str = "",
        design_name: str | None = None,
    ) -> tuple[Pose, MutationResult, MutationAnalysis, MutationContext]:
        """Evaluate one mutation and archive the complete scientific feedback."""
        if self.pending_design_id is not None:
            raise RuntimeError(
                "A mutation is already awaiting a decision. Accept or reject it before proposing another mutation."
            )

        wt_aa = self.pose.residue(position).name1()
        mutant_aa = mutant_aa.upper()
        if mutant_aa == wt_aa:
            raise ValueError(
                f"Residue {position} is already {wt_aa}. Choose a different amino acid."
            )

        context = get_mutation_context(
            pose=self.pose,
            position=position,
            mutant_aa=mutant_aa,
            radius=self.radius,
        )

        reference_pose = prepare_pose(
            self.pose,
            self.score_function,
            center_position=position,
            radius=self.radius,
        )
        mutant_pose = mutate_pose(
            self.pose,
            position=position,
            mutant_aa=mutant_aa,
        )
        mutant_pose = prepare_pose(
            mutant_pose,
            self.score_function,
            center_position=position,
            radius=self.radius,
        )

        analysis = analyze_mutation(
            wt_pose=reference_pose,
            mutant_pose=mutant_pose,
            score_function=self.score_function,
        )

        result = MutationResult(
            mutation=f"{wt_aa}{position}{mutant_aa}",
            position=position,
            wt_aa=wt_aa,
            mutant_aa=mutant_aa,
            previous_score=analysis.wt_total_score,
            mutant_score=analysis.mutant_total_score,
            delta_score=analysis.delta_total_score,
            scores=analysis.mutant_terms,
        )

        candidate_design = Design(
            sequence=mutant_pose.sequence(),
            parent_design_id=self.current_design_id,
            status="active",
            name=design_name,
            metadata={
                "mutation": result.mutation,
                "position": position,
                "wt_aa": wt_aa,
                "mutant_aa": mutant_aa,
                "hypothesis": hypothesis,
                "objective": objective,
            },
        )

        self._save_design_structure(candidate_design, mutant_pose)
        self.archive.add_design(candidate_design)

        interpretations = interpret_energy_changes(analysis)
        evidence = EvidenceEntry(
            source_type="computational",
            source_name="PyRosetta",
            summary=f"Rosetta evaluation of {result.mutation}.",
            design_id=candidate_design.id,
            data={
                "mutation": result.mutation,
                "position": position,
                "wt_aa": wt_aa,
                "mutant_aa": mutant_aa,
                "previous_score": result.previous_score,
                "mutant_score": result.mutant_score,
                "delta_score": result.delta_score,
                # Kept for backward compatibility with v0.3 frontend/export consumers.
                "score_terms": result.scores,
                # Full energetic comparison retained from v0.4 onward.
                "parent_score_terms": analysis.wt_terms,
                "mutant_score_terms": analysis.mutant_terms,
                "delta_score_terms": analysis.delta_terms,
                "improved_terms": analysis.improved_terms,
                "worsened_terms": analysis.worsened_terms,
                "interpretations": [asdict(item) for item in interpretations],
                "context": {
                    "position": context.position,
                    "wt_aa": context.wt_aa,
                    "mutant_aa": context.mutant_aa,
                    "radius_angstrom": self.radius,
                    "nearby_residues": [
                        asdict(residue) for residue in context.nearby_residues
                    ],
                },
                "preparation": {"radius_angstrom": self.radius},
            },
        )
        self.archive.add_evidence(evidence)

        self.pending_design_id = candidate_design.id
        self.pending_evidence_id = evidence.id
        self._autosave_archive()

        return mutant_pose, result, analysis, context

    def accept_mutation(
        self,
        mutant_pose: Pose,
        result: MutationResult,
        rationale: str = "",
        user_note: str | None = None,
    ) -> None:
        """Accept a proposed mutation."""
        candidate_design = self._get_pending_design()
        parent_design_id = candidate_design.parent_design_id
        if parent_design_id is None:
            raise RuntimeError("Pending design has no parent.")

        self.archive.add_decision(
            Decision(
                parent_design_id=parent_design_id,
                candidate_design_id=candidate_design.id,
                outcome="accepted",
                hypothesis=str(candidate_design.metadata.get("hypothesis", "")),
                objective=str(candidate_design.metadata.get("objective", "")),
                rationale=rationale,
                user_note=user_note,
            )
        )
        candidate_design.status = "active"
        self.pose = mutant_pose
        self.history.append(result)
        self.current_design_id = candidate_design.id
        self._clear_pending()
        self._autosave_archive()

    def reject_mutation(
        self,
        rationale: str = "",
        user_note: str | None = None,
    ) -> None:
        """Reject the currently pending mutation."""
        candidate_design = self._get_pending_design()
        parent_design_id = candidate_design.parent_design_id
        if parent_design_id is None:
            raise RuntimeError("Pending design has no parent.")

        self.archive.add_decision(
            Decision(
                parent_design_id=parent_design_id,
                candidate_design_id=candidate_design.id,
                outcome="rejected",
                hypothesis=str(candidate_design.metadata.get("hypothesis", "")),
                objective=str(candidate_design.metadata.get("objective", "")),
                rationale=rationale,
                user_note=user_note,
            )
        )
        candidate_design.status = "deprioritized"
        self._clear_pending()
        self._autosave_archive()

    def defer_mutation(
        self,
        rationale: str = "",
        user_note: str | None = None,
    ) -> None:
        """Defer the currently pending mutation."""
        candidate_design = self._get_pending_design()
        parent_design_id = candidate_design.parent_design_id
        if parent_design_id is None:
            raise RuntimeError("Pending design has no parent.")

        self.archive.add_decision(
            Decision(
                parent_design_id=parent_design_id,
                candidate_design_id=candidate_design.id,
                outcome="deferred",
                hypothesis=str(candidate_design.metadata.get("hypothesis", "")),
                objective=str(candidate_design.metadata.get("objective", "")),
                rationale=rationale,
                user_note=user_note,
            )
        )
        candidate_design.status = "deprioritized"
        self._clear_pending()
        self._autosave_archive()

    def _get_pending_design(self) -> Design:
        """Return the candidate awaiting a decision."""
        if self.pending_design_id is None:
            raise RuntimeError("No mutation is currently awaiting a decision.")
        try:
            return self.archive.designs[self.pending_design_id]
        except KeyError as error:
            raise RuntimeError("Pending design is missing from the archive.") from error

    def save_history_csv(self, output_path: str | Path) -> None:
        """Save accepted mutations from this session as CSV."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "step",
            "mutation",
            "position",
            "wt_aa",
            "mutant_aa",
            "previous_score",
            "mutant_score",
            "delta_score",
        ]
        rows: list[dict[str, object]] = []
        for step, result in enumerate(self.history, start=1):
            row: dict[str, object] = {
                "step": step,
                "mutation": result.mutation,
                "position": result.position,
                "wt_aa": result.wt_aa,
                "mutant_aa": result.mutant_aa,
                "previous_score": result.previous_score,
                "mutant_score": result.mutant_score,
                "delta_score": result.delta_score,
            }
            for term, value in result.scores.items():
                row[term] = value
                if term not in fieldnames:
                    fieldnames.append(term)
            rows.append(row)

        with output_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            if rows:
                writer.writerows(rows)

    def save_history_json(self, output_path: str | Path) -> None:
        """Save legacy accepted-mutation history."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "final_sequence": self.pose.sequence(),
            "accepted_mutations": [asdict(result) for result in self.history],
        }
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

    def _save_design_structure(
        self,
        design: Design,
        pose: Pose,
        label: str | None = None,
    ) -> None:
        """Save the PDB associated with a design."""
        if self.structures_dir is None:
            return

        structures_dir = Path(self.structures_dir)
        structures_dir.mkdir(parents=True, exist_ok=True)
        mutation = design.metadata.get("mutation", "design")
        chosen_label = label or design.name or mutation
        safe_label = (
            str(chosen_label)
            .strip()
            .replace("/", "_")
            .replace("\\", "_")
            .replace(" ", "_")
        ) or str(mutation)

        structure_path = structures_dir / f"{safe_label}.pdb"
        counter = 2
        while structure_path.exists():
            structure_path = structures_dir / f"{safe_label}_{counter}.pdb"
            counter += 1

        pose.dump_pdb(str(structure_path))
        design.structure_path = str(structure_path)

    def _autosave_archive(self) -> None:
        """Persist the project archive."""
        if self.archive_path is not None:
            self.archive.save(self.archive_path)

    def _clear_pending(self) -> None:
        """Clear the candidate currently awaiting a decision."""
        self.pending_design_id = None
        self.pending_evidence_id = None
