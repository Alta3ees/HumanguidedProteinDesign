from human_protein_design.analysis import MutationAnalysis
from human_protein_design.interpretation import (
    interpret_energy_changes,
)


def test_interpret_energy_changes():

    analysis = MutationAnalysis(
        wt_total_score=-20.0,
        mutant_total_score=-15.0,
        delta_total_score=5.0,
        wt_terms={
            "total_score": -20.0,
            "fa_atr": -100.0,
            "fa_rep": 20.0,
        },
        mutant_terms={
            "total_score": -15.0,
            "fa_atr": -105.0,
            "fa_rep": 25.0,
        },
        delta_terms={
            "total_score": 5.0,
            "fa_atr": -5.0,
            "fa_rep": 5.0,
        },
        improved_terms=[
            "fa_atr",
        ],
        worsened_terms=[
            "total_score",
            "fa_rep",
        ],
    )

    interpretations = interpret_energy_changes(
        analysis
    )

    assert len(interpretations) == 2

    assert interpretations[0].term in {
        "fa_atr",
        "fa_rep",
    }


def test_total_score_is_not_interpreted():

    analysis = MutationAnalysis(
        wt_total_score=-20.0,
        mutant_total_score=-21.0,
        delta_total_score=-1.0,
        wt_terms={
            "total_score": -20.0,
        },
        mutant_terms={
            "total_score": -21.0,
        },
        delta_terms={
            "total_score": -1.0,
        },
        improved_terms=[
            "total_score",
        ],
        worsened_terms=[],
    )

    interpretations = interpret_energy_changes(
        analysis
    )

    assert interpretations == []