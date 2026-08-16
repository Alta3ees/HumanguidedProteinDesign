from human_protein_design.analysis import ENERGY_TOLERANCE, classify_energy_changes

def test_energy_tolerance_classification():
    delta_terms = {
        "fa_atr": -2.0,
        "fa_rep": 1.5,
        "fa_sol": ENERGY_TOLERANCE / 2,
        "fa_elec": -ENERGY_TOLERANCE / 2,
    }

    improved_terms, worsened_terms = (
     classify_energy_changes(delta_terms)
    )

    assert improved_terms == ["fa_atr"]
    assert worsened_terms == ["fa_rep"]

def test_zero_changes_are_ignored():

    improved, worsened = (
        classify_energy_changes(
            {
                "fa_atr": 0.0,
                "fa_rep": 0.0,
            }
        )
    )

    assert improved == []
    assert worsened == []

def test_multiple_terms_are_classified():

    improved, worsened = (
        classify_energy_changes(
            {
                "fa_atr": -3.0,
                "fa_sol": -1.0,
                "fa_rep": 2.0,
                "fa_elec": 0.5,
            }
        )
    )

    assert improved == [
        "fa_atr",
        "fa_sol",
    ]

    assert worsened == [
        "fa_rep",
        "fa_elec",
    ]