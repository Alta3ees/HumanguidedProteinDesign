import pyrosetta
from pathlib import Path
from datetime import datetime

from human_protein_design.scoring import (
    get_standard_score_function,
    initialize_pyrosetta,
)

from human_protein_design.analysis import (
    MutationAnalysis,
)

from human_protein_design.session import (
    DesignSession,
)
from human_protein_design.context import (
    MutationContext,
)

from human_protein_design.interpretation import (
    interpret_energy_changes,
)

PDB_PATH = "data/raw/1PGA.pdb"
OUTPUT_DIR = Path(
    "data/results/human_guided_sessions"
)


def print_result(
    result,
    analysis: MutationAnalysis,
    context: MutationContext,
) -> None:
    """Print mutation feedback."""

    print("\nMutation result")
    print("-" * 50)

    print(
        f"Mutation:       "
        f"{result.mutation}"
    )

    print(
        f"Previous score: "
        f"{analysis.wt_total_score:.3f}"
    )

    print(
        f"Mutant score:   "
        f"{analysis.mutant_total_score:.3f}"
    )

    print(
        f"ΔScore:         "
        f"{analysis.delta_total_score:+.3f} REU"
    )

    print("\nEnergy changes")
    print("-" * 50)

    print(
        f"{'Term':<20}"
        f"{'Previous':>10}"
        f"{'Mutant':>10}"
        f"{'Δ':>10}"
    )

    print("-" * 50)

    for term, delta in analysis.delta_terms.items():
        if term == "total_score":
         continue

        previous = analysis.wt_terms[term]
        mutant = analysis.mutant_terms[term]

        print(
            f"{term:<20}"
            f"{previous:>10.3f}"
            f"{mutant:>10.3f}"
            f"{delta:>+10.3f}"
        )

    if analysis.improved_terms:
        

        print("\nImproved terms")

        for term in analysis.improved_terms:
            if term == "total_score":
                continue
            print(
                f"  ↓ {term:<18}"
                f"{analysis.delta_terms[term]:+.3f}"
            )

        print("\nNearby residues")
        print("-" * 50)

        for residue in context.nearby_residues:
            print(
                f"{residue.amino_acid}"
                f"{residue.position:<6}"
                f"{residue.distance:>8.2f} Å"
            )

    if analysis.worsened_terms:
        
        print("\nWorsened terms")

        for term in analysis.worsened_terms:
            if term == "total_score":
                continue

            print(
                f"  ↑ {term:<18}"
                f"{analysis.delta_terms[term]:+.3f}"
            )
        print("\nNearby residues")
        print("-" * 50)

        for residue in context.nearby_residues:
            print(
                f"{residue.amino_acid}"
                f"{residue.position:<6}"
                f"{residue.distance:>8.2f} Å"
            )

    interpretations = interpret_energy_changes(
      analysis
    )

    if interpretations:
    
        print("\nInterpretation")
        print("-" * 50)
    
        for item in interpretations:
        
            symbol = (
                "↓"
                if item.direction == "improved"
                else "↑"
            )
    
            print(
                f"{symbol} {item.term:<16}"
                f"{item.delta:+8.3f}  "
                f"{item.message}"
            )

def main():

    initialize_pyrosetta()

    pose = pyrosetta.pose_from_pdb(
        PDB_PATH
    )

    score_function = (
        get_standard_score_function()
    )

    session = DesignSession(
        pose=pose,
        score_function=score_function,
    )

    print("\nHuman-Guided Protein Design")
    print("=" * 50)

    while True:

        print(
            f"\nCurrent sequence:\n"
            f"{session.pose.sequence()}"
        )

        command = input(
            "\nPosition "
            "(or 'q' to quit): "
        ).strip()

        if command.lower() == "q":
            break

        try:
            position = int(command)

        except ValueError:
            print(
                "Position must be an integer."
            )
            continue

        if not (
            1
            <= position
            <= session.pose.total_residue()
        ):
            print(
                "Position outside protein."
            )
            continue

        current_aa = session.pose.residue(
            position
        ).name1()

        print(
            f"Current residue: "
            f"{current_aa}{position}"
        )

        mutant_aa = input(
            "Mutate to: "
        ).strip().upper()

        try:

            mutant_pose, result, analysis, context = (
                session.evaluate_mutation(
                    position,
                        mutant_aa,
                )
            )

        except ValueError as error:

            print(error)
            continue

        

        print_result(
            result,
            analysis,
            context,
        )

        decision = input(
            "\nAccept mutation? [y/n]: "
        ).strip().lower()

        if decision == "y":

            session.accept_mutation(
                mutant_pose,
                result,
            )

            print(
                f"\nAccepted "
                f"{result.mutation}"
            )

        else:

            print(
                f"\nRejected "
                f"{result.mutation}"
            )

    print("\nDesign session finished.")

    if session.history:

        print("\nAccepted mutations:")

        for result in session.history:

            print(
                f"  {result.mutation:<8}"
                f"ΔScore "
                f"{result.delta_score:+.3f}"
            )

    else:

        print(
            "\nNo mutations were accepted."
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    session_dir = (
        OUTPUT_DIR
        / f"session_{timestamp}"
    )

    session_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    csv_path = (
        session_dir
        / "history.csv"
    )

    json_path = (
        session_dir
        / "history.json"
    )

    pdb_path = (
        session_dir
        / "final_design.pdb"
    )

    session.save_history_csv(
        csv_path
    )

    session.save_history_json(
        json_path
    )

    session.pose.dump_pdb(
        str(pdb_path)
    )

    print(
        "\nSession saved to:"
        f"\n{session_dir}"
    )


if __name__ == "__main__":
    main()