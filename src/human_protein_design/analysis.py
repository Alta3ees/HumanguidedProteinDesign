"""Interpret mutation-induced Rosetta energy changes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyrosetta.rosetta.core.pose import Pose
else:
    Pose = Any

ENERGY_TOLERANCE = 1e-6


@dataclass
class MutationAnalysis:
    """Summary of energetic changes caused by a mutation."""

    wt_total_score: float
    mutant_total_score: float
    delta_total_score: float

    wt_terms: dict[str, float]
    mutant_terms: dict[str, float]
    delta_terms: dict[str, float]

    improved_terms: list[str]
    worsened_terms: list[str]


def analyze_mutation(
    wt_pose: Pose,
    mutant_pose: Pose,
    score_function,
) -> MutationAnalysis:
    """Compare a mutant pose against the current accepted pose.

    Negative delta values indicate a more favorable Rosetta energy.
    Positive delta values indicate a less favorable Rosetta energy.

    PyRosetta-backed scoring is imported lazily here so pure analysis/archive
    modules remain importable for tooling and portability tests. Actual mutation
    evaluation still requires the standard HGD environment with PyRosetta.
    """
    from human_protein_design.scoring import get_score_terms

    wt_total = score_function(wt_pose)
    mutant_total = score_function(mutant_pose)

    wt_terms = get_score_terms(wt_pose, score_function)
    mutant_terms = get_score_terms(mutant_pose, score_function)

    delta_terms = {
        term: mutant_terms[term] - wt_terms[term]
        for term in wt_terms
        if term in mutant_terms
    }
    improved_terms, worsened_terms = classify_energy_changes(delta_terms)

    return MutationAnalysis(
        wt_total_score=wt_total,
        mutant_total_score=mutant_total,
        delta_total_score=mutant_total - wt_total,
        wt_terms=wt_terms,
        mutant_terms=mutant_terms,
        delta_terms=delta_terms,
        improved_terms=improved_terms,
        worsened_terms=worsened_terms,
    )


def classify_energy_changes(
    delta_terms: dict[str, float],
) -> tuple[list[str], list[str]]:
    """Classify meaningful favorable and unfavorable energy changes."""
    improved_terms = [
        term
        for term, delta in delta_terms.items()
        if delta < -ENERGY_TOLERANCE
    ]
    worsened_terms = [
        term
        for term, delta in delta_terms.items()
        if delta > ENERGY_TOLERANCE
    ]
    return improved_terms, worsened_terms
