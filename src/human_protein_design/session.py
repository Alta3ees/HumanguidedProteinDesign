"""Human-guided protein design session utilities."""

import csv
import json

from dataclasses import asdict, dataclass, field
from pathlib import Path

from pyrosetta.rosetta.core.pose import Pose

from human_protein_design.analysis import (
    MutationAnalysis,
    analyze_mutation,
)
from human_protein_design.mutation import mutate_pose
from human_protein_design.scan import prepare_pose
from human_protein_design.context import (
    MutationContext,
    get_mutation_context,
)

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

    radius: float = 8.0

    history: list[MutationResult] = field(
        default_factory=list
    )

    def evaluate_mutation(
        self,
        position: int,
        mutant_aa: str,
    ) -> tuple[
        Pose,
        MutationResult,
        MutationAnalysis,
        MutationContext,
    ]:
        """
        Evaluate one mutation without accepting it.

        Both the reference and mutant structures undergo
        the same local preparation protocol before scoring.
        """

        wt_aa = self.pose.residue(
            position
        ).name1()

        mutant_aa = mutant_aa.upper()

        if mutant_aa == wt_aa:
            raise ValueError(
                f"Residue {position} is already {wt_aa}. "
                "Choose a different amino acid."
            )
        context = get_mutation_context(
            pose=self.pose,
            position=position,
            mutant_aa=mutant_aa,
            radius=self.radius,
        )
        # --------------------------------
        # Prepare reference structure
        # --------------------------------

        reference_pose = prepare_pose(
            self.pose,
            self.score_function,
            center_position=position,
            radius=self.radius,
        )

        # --------------------------------
        # Create and prepare mutation
        # --------------------------------

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

        # --------------------------------
        # Compare prepared structures
        # --------------------------------

        analysis = analyze_mutation(
            wt_pose=reference_pose,
            mutant_pose=mutant_pose,
            score_function=self.score_function,
        )

        result = MutationResult(
            mutation=(
                f"{wt_aa}{position}{mutant_aa}"
            ),
            position=position,
            wt_aa=wt_aa,
            mutant_aa=mutant_aa,
            previous_score=(
                analysis.wt_total_score
            ),
            mutant_score=(
                analysis.mutant_total_score
            ),
            delta_score=(
                analysis.delta_total_score
            ),
            scores=(
                analysis.mutant_terms
            ),
        )

        return (
            mutant_pose,
            result,
            analysis,
            context,
        )

    def accept_mutation(
        self,
        mutant_pose: Pose,
        result: MutationResult,
    ) -> None:
        """Accept a proposed mutation."""

        self.pose = mutant_pose

        self.history.append(result)

    def save_history_csv(
        self,
        output_path: str | Path,
        ) -> None:
        """Save accepted mutation history as CSV."""

        output_path = Path(output_path)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

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

        rows = []

        for step, result in enumerate(
            self.history,
            start=1,
        ):
            row = {
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

        with output_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
            )

            writer.writeheader()

            if rows:
                writer.writerows(rows)

    def save_history_json(
        self,
        output_path: str | Path,
    ) -> None:
        """Save the design session as JSON."""

        output_path = Path(output_path)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = {
            "final_sequence": (
                self.pose.sequence()
            ),
            "accepted_mutations": [
                asdict(result)
                for result in self.history
            ],
        }

        with output_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                data,
                file,
                indent=2,
            )