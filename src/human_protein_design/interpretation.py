from dataclasses import dataclass

from human_protein_design.analysis import MutationAnalysis


@dataclass
class EnergyInterpretation:
    """Human-readable interpretation of one energy-term change."""

    term: str
    delta: float
    direction: str
    message: str


TERM_MESSAGES = {
    "fa_atr": {
        "improved": "More favorable attractive atomic interactions.",
        "worsened": "Less favorable attractive atomic interactions.",
    },
    "fa_rep": {
        "improved": "Reduced steric repulsion.",
        "worsened": "Increased steric repulsion.",
    },
    "fa_sol": {
        "improved": "More favorable implicit-solvation contribution.",
        "worsened": "Less favorable implicit-solvation contribution.",
    },
    "fa_elec": {
        "improved": "More favorable electrostatic contribution.",
        "worsened": "Less favorable electrostatic contribution.",
    },
    "hbond_sr_bb": {
        "improved": "More favorable short-range backbone hydrogen bonding.",
        "worsened": "Less favorable short-range backbone hydrogen bonding.",
    },
    "hbond_lr_bb": {
        "improved": "More favorable long-range backbone hydrogen bonding.",
        "worsened": "Less favorable long-range backbone hydrogen bonding.",
    },
    "hbond_bb_sc": {
        "improved": "More favorable backbone–side-chain hydrogen bonding.",
        "worsened": "Less favorable backbone–side-chain hydrogen bonding.",
    },
    "hbond_sc": {
        "improved": "More favorable side-chain hydrogen bonding.",
        "worsened": "Less favorable side-chain hydrogen bonding.",
    },
}


def interpret_energy_changes(
    analysis: MutationAnalysis,
) -> list[EnergyInterpretation]:
    """Convert meaningful Rosetta term changes into readable feedback."""

    interpretations = []

    for term, delta in analysis.delta_terms.items():

        if term == "total_score":
            continue

        if term in analysis.improved_terms:
            direction = "improved"

        elif term in analysis.worsened_terms:
            direction = "worsened"

        else:
            continue

        messages = TERM_MESSAGES.get(term)

        if messages is None:
            message = (
                "More favorable score contribution."
                if direction == "improved"
                else "Less favorable score contribution."
            )
        else:
            message = messages[direction]

        interpretations.append(
            EnergyInterpretation(
                term=term,
                delta=delta,
                direction=direction,
                message=message,
            )
        )

    interpretations.sort(
        key=lambda item: abs(item.delta),
        reverse=True,
    )

    return interpretations