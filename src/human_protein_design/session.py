"""Human-guided protein design session utilities."""

from dataclasses import dataclass, field

from pyrosetta.rosetta.core.pose import Pose

from human_protein_design.scan import prepare_pose
from human_protein_design.mutation import mutate_pose
from human_protein_design.scoring import get_score_terms

import csv
import json

from dataclasses import asdict, dataclass, field
from pathlib import Path

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

OUTPUT_DIR = Path(
    "data/results/human_guided_sessions"
)

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
    ) -> tuple[Pose, MutationResult]:
        """Evaluate one mutation !!!without accepting it!!! aka does not modify the current protein.
        Only accept_mutation() does."""

        wt_aa = self.pose.residue(
            position
        ).name1()

        mutant_aa = mutant_aa.upper()
        
        if mutant_aa == wt_aa:
            raise ValueError(
                 f"Residue {position} is already {wt_aa}. "
                 "Choose a different amino acid."
            )
        # --------------------------------
        # Prepare current structure
        # --------------------------------

        reference_pose = prepare_pose(
            self.pose,
            self.score_function,
            center_position=position,
            radius=self.radius,
        )

        reference_scores = get_score_terms(
            reference_pose,
            self.score_function,
        )

        # --------------------------------
        # Create mutation
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

        mutant_scores = get_score_terms(
            mutant_pose,
            self.score_function,
        )

        previous_score = (
            reference_scores["total_score"]
        )

        mutant_score = (
            mutant_scores["total_score"]
        )

        result = MutationResult(
            mutation=(
                f"{wt_aa}{position}{mutant_aa}"
            ),
            position=position,
            wt_aa=wt_aa,
            mutant_aa=mutant_aa,
            previous_score=previous_score,
            mutant_score=mutant_score,
            delta_score=(
                mutant_score
                - previous_score
            ),
            scores=mutant_scores,
        )

        return mutant_pose, result

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

        if not self.history:
            return

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

            rows.append(row)

        with output_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=rows[0].keys(),
            )

            writer.writeheader()
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
            "final_sequence": self.pose.sequence(),
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