from pathlib import Path

from human_protein_design.archive import (
    DesignProject,
)


PROJECT_DIR = Path(
    "data/projects/gb1_design"
)


def choose_design(project):
    """Let the user choose a design to review."""

    designs = list(
        project.archive.designs.values()
    )

    if not designs:
        raise RuntimeError(
            "Project contains no designs."
        )

    print("\nAvailable designs")
    print("-" * 70)

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

        decision_text = (
            latest_decision.outcome
            if latest_decision is not None
            else "none"
        )

        print(
            f"{index:>3}. "
            f"{lineage:<35} "
            f"status={design.status:<15} "
            f"decision={decision_text}"
        )

    while True:

        choice = input(
            "\nChoose design number: "
        ).strip()

        try:
            index = int(
                choice
            )

        except ValueError:
            print(
                "Enter a valid number."
            )
            continue

        if not (
            1 <= index <= len(designs)
        ):
            print(
                "Design number outside range."
            )
            continue

        return designs[
            index - 1
        ]


def print_design_header(
    project,
    design,
) -> None:
    """Print core design information."""

    archive = project.archive

    print("\nDESIGN REVIEW")
    print("=" * 70)

    print(
        "\nDesign ID:"
    )
    print(
        f"  {design.id}"
    )

    print(
        "\nLineage:"
    )
    print(
        "  "
        + archive.get_lineage_label(
            design.id
        )
    )

    mutations = (
        archive.get_lineage_mutations(
            design.id
        )
    )

    print(
        "\nAccumulated mutations:"
    )

    if mutations:

        print(
            "  "
            + ", ".join(
                mutations
            )
        )

    else:

        print(
            "  None (root design)"
        )

    print(
        "\nCurrent status:"
    )
    print(
        f"  {design.status}"
    )

    print(
        "\nCreated:"
    )
    print(
        f"  {design.created_at}"
    )

    print(
        "\nSequence:"
    )
    print(
        f"  {design.sequence}"
    )

    print(
        "\nStructure:"
    )

    if design.structure_path:
        print(
            f"  {design.structure_path}"
        )
    else:
        print(
            "  No structure attached."
        )


def print_decisions(
    project,
    design,
) -> None:
    """Print complete decision history."""

    decisions = (
        project.archive.get_design_decisions(
            design.id
        )
    )

    print("\nDECISION HISTORY")
    print("=" * 70)

    if not decisions:
        print(
            "\nNo decisions recorded."
        )
        return

    for index, decision in enumerate(
        decisions,
        start=1,
    ):

        print(
            f"\nDecision {index}"
        )
        print(
            "-" * 70
        )

        print(
            f"Date:      "
            f"{decision.created_at}"
        )

        print(
            f"Outcome:   "
            f"{decision.outcome}"
        )

        if decision.hypothesis:
            print(
                f"Hypothesis:"
                f" {decision.hypothesis}"
            )

        if decision.objective:
            print(
                f"Objective: "
                f"{decision.objective}"
            )

        if decision.rationale:
            print(
                f"Rationale: "
                f"{decision.rationale}"
            )

        if decision.user_note:
            print(
                f"User note: "
                f"{decision.user_note}"
            )

        if decision.program_comment:
            print(
                f"Program:   "
                f"{decision.program_comment}"
            )


def print_evidence(
    project,
    design,
) -> None:
    """Print all evidence associated with a design."""

    evidence_entries = (
        project.archive.get_design_evidence(
            design.id
        )
    )

    print("\nEVIDENCE")
    print("=" * 70)

    if not evidence_entries:
        print(
            "\nNo evidence recorded."
        )
        return

    grouped = {
        "computational": [],
        "experimental": [],
        "literature": [],
        "note": [],
    }

    for entry in evidence_entries:

        grouped.setdefault(
            entry.source_type,
            [],
        ).append(
            entry
        )

    for source_type, entries in grouped.items():

        if not entries:
            continue

        print(
            f"\n{source_type.upper()}"
        )
        print(
            "-" * 70
        )

        for index, entry in enumerate(
            entries,
            start=1,
        ):

            print(
                f"\n[{index}] "
                f"{entry.source_name}"
            )

            print(
                f"Date: "
                f"{entry.created_at}"
            )

            print(
                f"Summary: "
                f"{entry.summary}"
            )

            if entry.data:

                print(
                    "Data:"
                )

                for key, value in (
                    entry.data.items()
                ):

                    if key == "score_terms":

                        print(
                            "  score_terms:"
                        )

                        for (
                            term,
                            score,
                        ) in value.items():

                            if isinstance(score, float):
                                score_text = f"{score:.2f}"
                            else:
                                score_text = str(score)


                            print(
                                f"    "
                                f"{term:<18}"
                                f"{score}"
                            )

                        continue

                    if key == "preparation":

                        print(
                            "  preparation:"
                        )

                        for (
                            parameter,
                            parameter_value,
                        ) in value.items():

                            print(
                                f"    "
                                f"{parameter}: "
                                f"{parameter_value}"
                            )

                        continue
                    if isinstance(value, float):
                        value_text = f"{value:.2f}"
                    else:
                        value_text = str(value)

                    print(
                        f"  {key}: "
                        f"{value}"
                    )

            if entry.notes:

                print(
                    f"Notes: "
                    f"{entry.notes}"
                )

            if entry.file_paths:

                print(
                    "Files:"
                )

                for path in (
                    entry.file_paths
                ):
                    file_path = Path(
                    path
                )

                    if not file_path.is_absolute():

                        file_path = (
                            project.root_dir
                            / file_path
                        )

                    exists = Path(
                        path
                    ).exists()

                    state = (
                        "found"
                        if exists
                        else "missing"
                    )

                    print(
                        f"  [{state}] "
                        f"{path}"
                    )

            if entry.references:

                print(
                    "References:"
                )

                for reference in (
                    entry.references
                ):

                    print(
                        f"  {reference}"
                    )


def print_summary(
    project,
    design,
) -> None:
    """Print a compact summary of the design record."""

    archive = project.archive

    decisions = (
        archive.get_design_decisions(
            design.id
        )
    )

    evidence = (
        archive.get_design_evidence(
            design.id
        )
    )

    evidence_counts: dict[str, int] = {}

    for entry in evidence:

        evidence_counts[
            entry.source_type
        ] = (
            evidence_counts.get(
                entry.source_type,
                0,
            )
            + 1
        )

    latest_decision = (
        archive.get_latest_decision(
            design.id
        )
    )

    print("\nSUMMARY")
    print("=" * 70)

    print(
        f"\nLineage: "
        f"{archive.get_lineage_label(design.id)}"
    )

    print(
        f"Status:  "
        f"{design.status}"
    )

    print(
        "Latest decision: "
        + (
            latest_decision.outcome
            if latest_decision
            else "none"
        )
    )

    print(
        f"Decisions recorded: "
        f"{len(decisions)}"
    )

    print(
        f"Evidence entries:   "
        f"{len(evidence)}"
    )

    if evidence_counts:

        print(
            "\nEvidence breakdown:"
        )

        for (
            source_type,
            count,
        ) in evidence_counts.items():

            print(
                f"  "
                f"{source_type:<15}"
                f"{count}"
            )


def main() -> None:
    """Review the full scientific history of one design."""

    project = DesignProject.load(
        name="GB1 Human-Guided Design",
        root_dir=PROJECT_DIR,
    )

    design = choose_design(
        project
    )

    print_design_header(
        project,
        design,
    )

    print_decisions(
        project,
        design,
    )

    print_evidence(
        project,
        design,
    )

    print_summary(
        project,
        design,
    )


if __name__ == "__main__":
    main()