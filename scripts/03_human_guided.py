import pyrosetta
from pathlib import Path
from datetime import datetime

from human_protein_design.scoring import (
    get_standard_score_function,
    initialize_pyrosetta,
)

from human_protein_design.session import (
    DesignSession,
)


PDB_PATH = "data/raw/1PGA.pdb"
OUTPUT_DIR = Path(
    "data/results/human_guided_sessions"
)

def print_result(result) -> None:
    """Print mutation feedback."""

    print("\nMutation result")
    print("-" * 40)

    print(
        f"Mutation:       "
        f"{result.mutation}"
    )

    print(
        f"Previous score: "
        f"{result.previous_score:.3f}"
    )

    print(
        f"Mutant score:   "
        f"{result.mutant_score:.3f}"
    )

    print(
        f"ΔScore:         "
        f"{result.delta_score:+.3f} REU"
    )

    print("\nEnergy terms")
    print("-" * 40)

    for term, value in result.scores.items():

        if term == "total_score":
            continue

        print(
            f"{term:<20}"
            f"{value:>10.3f}"
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
    print("=" * 40)

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

            mutant_pose, result = (
                session.evaluate_mutation(
                    position,
                    mutant_aa,
                )
            )

        except ValueError as error:

            print(error)
            continue

        print_result(result)

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