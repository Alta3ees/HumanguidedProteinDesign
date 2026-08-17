import pyrosetta

from datetime import datetime
from pathlib import Path

from human_protein_design.analysis import (
    MutationAnalysis,
)
from human_protein_design.archive import (
    DesignProject,
)
from human_protein_design.context import (
    MutationContext,
)
from human_protein_design.interpretation import (
    interpret_energy_changes,
)
from human_protein_design.scoring import (
    get_standard_score_function,
    initialize_pyrosetta,
)
from human_protein_design.session import (
    DesignSession,
)


PDB_PATH = Path(
    "data/raw/1PGA.pdb"
)

PROJECT_DIR = Path(
    "data/projects/gb1_design"
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

    # --------------------------------
    # Energy changes
    # --------------------------------

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

        previous = analysis.wt_terms[
            term
        ]

        mutant = analysis.mutant_terms[
            term
        ]

        print(
            f"{term:<20}"
            f"{previous:>10.3f}"
            f"{mutant:>10.3f}"
            f"{delta:>+10.3f}"
        )

    # --------------------------------
    # Improved terms
    # --------------------------------

    if analysis.improved_terms:

        print("\nImproved terms")

        for term in analysis.improved_terms:

            if term == "total_score":
                continue

            print(
                f"  ↓ {term:<18}"
                f"{analysis.delta_terms[term]:+.3f}"
            )

    # --------------------------------
    # Worsened terms
    # --------------------------------

    if analysis.worsened_terms:

        print("\nWorsened terms")

        for term in analysis.worsened_terms:

            if term == "total_score":
                continue

            print(
                f"  ↑ {term:<18}"
                f"{analysis.delta_terms[term]:+.3f}"
            )

    # --------------------------------
    # Structural neighborhood
    # --------------------------------

    if context.nearby_residues:

        print("\nNearby residues")
        print("-" * 50)

        for residue in context.nearby_residues:

            print(
                f"{residue.amino_acid}"
                f"{residue.position:<6}"
                f"{residue.distance:>8.2f} Å"
            )

    # --------------------------------
    # Interpretation
    # --------------------------------

    interpretations = (
        interpret_energy_changes(
            analysis
        )
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


def get_latest_design(
    project: DesignProject,
):
    """
    Return the most recently created active design.

    For now this is the design from which a new session
    automatically resumes.
    """

    active_designs = [
        design
        for design
        in project.archive.designs.values()
        if design.status == "active"
    ]

    if not active_designs:
        return None

    return max(
        active_designs,
        key=lambda design: design.created_at,
    )


def resolve_structure_path(
    project: DesignProject,
    structure_path: str,
) -> Path:
    """Resolve a design's stored structure path."""

    path = Path(
        structure_path
    )

    if path.is_absolute():
        return path

    # Preferred project-relative representation.
    candidate = (
        project.root_dir
        / path
    )

    if candidate.exists():
        return candidate

    # Compatibility with paths already stored relative
    # to the repository working directory.
    if path.exists():
        return path

    raise FileNotFoundError(
        "Could not find stored structure: "
        f"{structure_path}"
    )



def choose_starting_design(
    project: DesignProject,
):
    """Let the user choose which design to continue from."""

    designs = sorted(
        project.archive.designs.values(),
        key=lambda design: design.created_at,
    )

    if not designs:
        return None

    print("\nAvailable starting designs")
    print("-" * 75)

    for index, design in enumerate(
        designs,
        start=1,
    ):
        lineage = (
            project.archive.get_lineage_label(
                design.id
            )
        )

        latest_decision = (
            project.archive.get_latest_decision(
                design.id
            )
        )

        decision = (
            latest_decision.outcome
            if latest_decision is not None
            else "none"
        )

        print(
            f"{index:>3}. "
            f"{lineage:<35} "
            f"status={design.status:<15} "
            f"decision={decision}"
        )

    while True:

        choice = input(
            "\nContinue from design number: "
        ).strip()

        try:
            index = int(
                choice
            )

        except ValueError:

            print(
                "Enter a valid design number."
            )
            continue

        if not (
            1 <= index <= len(designs)
        ):

            print(
                "Design number outside range."
            )
            continue

        design = designs[
            index - 1
        ]

        if design.structure_path is None:

            print(
                "That design has no saved structure."
            )
            continue

        return design


VALID_AMINO_ACIDS = set(
    "ACDEFGHIKLMNPQRSTVWY"
)


def ask_mutant_aa(
    position: int,
    current_aa: str,
) -> str:
    """Ask until a valid mutation is entered."""

    while True:

        mutant_aa = input(
            "Mutate to: "
        ).strip().upper()

        if len(mutant_aa) != 1:
            print(
                "Enter a single amino-acid code "
                "(e.g. A, W, K)."
            )
            continue

        if mutant_aa not in VALID_AMINO_ACIDS:
            print(
                f"'{mutant_aa}' is not a valid "
                "standard amino-acid code."
            )
            continue

        if mutant_aa == current_aa:
            print(
                f"Residue {position} is already "
                f"{current_aa}. Choose a different "
                "amino acid."
            )
            continue

        return mutant_aa

def main() -> None:
    """Run the human-guided design workflow."""

    initialize_pyrosetta()

    score_function = (
        get_standard_score_function()
    )

    # --------------------------------
    # Load project
    # --------------------------------

    project = DesignProject.load(
        name="GB1 Human-Guided Design",
        root_dir=PROJECT_DIR,
    )

    # --------------------------------
    # Create session directory NOW
    #
    # This must happen before DesignSession is
    # created because structures/archive data are
    # written during the session.
    # --------------------------------

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    session_dir = (
        project.sessions_dir
        / f"session_{timestamp}"
    )

    session_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------
    # Start or resume project
    # --------------------------------

    if not project.archive.designs:

        print(
            "\nStarting new design project."
        )

        pose = pyrosetta.pose_from_pdb(
            str(PDB_PATH)
        )

        session = DesignSession(
            pose=pose,
            score_function=score_function,
            archive=project.archive,
            archive_path=project.archive_path,
            structures_dir=project.structures_dir,
            output_dir=session_dir,
        )

    else:

        current_design = (
            choose_starting_design(
                project
            )
        )

        if current_design is None:
            raise RuntimeError(
                "No design could be selected."
            )

        structure_path = (
            resolve_structure_path(
                project,
                current_design.structure_path,
            )
        )

        pose = pyrosetta.pose_from_pdb(
            str(structure_path)
        )

        session = DesignSession(
            pose=pose,
            score_function=score_function,
            archive=project.archive,
            current_design_id=(
                current_design.id
            ),
            archive_path=project.archive_path,
            structures_dir=project.structures_dir,
            output_dir=session_dir,
        )

        print(
            "\nContinuing existing project."
        )

        print(
            "Starting lineage:"
        )

        print(
            "  "
            + project.archive.get_lineage_label(
                current_design.id
            )
        )

    # --------------------------------
    # CLI
    # --------------------------------

    print(
        "\nHuman-Guided Protein Design"
    )
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
            position = int(
                command
            )

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

        current_aa = (
            session.pose.residue(
                position
            ).name1()
        )

        print(
            f"Current residue: "
            f"{current_aa}{position}"
        )

        mutant_aa = ask_mutant_aa(
            position,
            current_aa,
        )

        design_name = input(
            "Design name "
            "(Enter for automatic): "
        ).strip()

        if not design_name:
            design_name = None

        hypothesis = input(
            "Hypothesis "
            "(what do you expect this mutation to do?): "
        ).strip()

        objective = input(
            "Objective "
            "(what are you trying to improve/test?): "
        ).strip()

        try:

            (
                mutant_pose,
                result,
                analysis,
                context,
            ) = session.evaluate_mutation(
                    position,
                    mutant_aa,
                    hypothesis=hypothesis,
                    objective=objective,
                    design_name=design_name,
                )

        except (
            ValueError,
            RuntimeError,
        ) as error:

            print(
                error
            )
            continue

        print_result(
            result,
            analysis,
            context,
        )

        # --------------------------------
        # Human decision
        # --------------------------------

        while True:

            decision = input(
                "\nAccept mutation? [y/n]: "
            ).strip().lower()

            if decision in {
                "y",
                "n",
            }:
                break

            print(
                "Please enter 'y' or 'n'."
            )

        rationale = input(
            "\nRationale "
            "(why are you making this decision?): "
        ).strip()

        if decision == "y":

            session.accept_mutation(
                mutant_pose,
                result,
                rationale=rationale,
            )

            print(
                f"\nAccepted "
                f"{result.mutation}"
            )

            if (
                session.current_design_id
                is not None
            ):

                print(
                    "Lineage: "
                    + session.archive
                    .get_lineage_label(
                        session.current_design_id
                    )
                )

        else:

            session.reject_mutation(
                rationale=rationale,
            )

            print(
                f"\nRejected "
                f"{result.mutation}"
            )

            print(
                "Candidate retained "
                "in design archive."
            )

    # --------------------------------
    # Session summary
    # --------------------------------

    print(
        "\nDesign session finished."
    )

    if session.history:

        print(
            "\nAccepted mutations "
            "this session:"
        )

        for result in session.history:

            print(
                f"  {result.mutation:<8}"
                f"ΔScore "
                f"{result.delta_score:+.3f}"
            )

    else:

        print(
            "\nNo mutations were accepted "
            "during this session."
        )

    # --------------------------------
    # Legacy session outputs
    # --------------------------------

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

    # Make absolutely sure canonical archive
    # is persisted when session exits.
    project.archive = (
        session.archive
    )

    project.save()

    print(
        "\nSession saved to:"
        f"\n{session_dir}"
    )

    print(
        "\nProject archive:"
        f"\n{project.archive_path}"
    )

    if (
        session.current_design_id
        is not None
    ):

        print(
            "\nCurrent design lineage:"
        )

        print(
            "  "
            + session.archive
            .get_lineage_label(
                session.current_design_id
            )
        )


if __name__ == "__main__":
    main()