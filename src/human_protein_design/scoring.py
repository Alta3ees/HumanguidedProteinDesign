"""Protein structure scoring utilities using PyRosetta."""

import pyrosetta
from pyrosetta.rosetta.core.pose import Pose
from pyrosetta.rosetta.core.scoring import ScoreType


SCORE_TERMS = [
    "fa_atr",
    "fa_rep",
    "fa_sol",
    "fa_elec",
    "hbond_sr_bb",
    "hbond_lr_bb",
    "hbond_bb_sc",
    "hbond_sc",
]


def initialize_pyrosetta() -> None:
    """Initialize PyRosetta with reproducible sampling."""
    pyrosetta.init(
        "-mute all "
        "-run:constant_seed "
        "-run:jran 1111111"
    )

def get_standard_score_function():
    """Return Rosetta's standard full-atom score function."""
    return pyrosetta.get_fa_scorefxn()


def get_score_terms(
    pose: Pose,
    score_function,
) -> dict[str, float]:
    """Return selected weighted Rosetta score terms."""

    total_score = float(score_function(pose))

    energies = pose.energies().total_energies()

    scores = {
        "total_score": total_score,
    }

    for term in SCORE_TERMS:
        score_type = getattr(ScoreType, term)

        raw_energy = float(energies[score_type])
        weight = float(score_function.get_weight(score_type))

        scores[term] = raw_energy * weight

    return scores