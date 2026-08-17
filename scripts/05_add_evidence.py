from pathlib import Path

from human_protein_design.archive import (
    DesignProject,
    add_external_evidence,
)


PROJECT_DIR = Path(
    "data/projects/gb1_design"
)


def choose_design(project):
    """Let the user choose a design from the archive."""

    designs = list(
        project.archive.designs.values()
    )

    if not designs:
        raise RuntimeError(
            "Project contains no designs."
        )

    print("\nAvailable designs")
    print("-" * 60)

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
            f"{lineage:<30} "
            f"status={design.status:<15} "
            f"decision={decision_text}"
        )

    while True:

        choice = input(
            "\nChoose design number: "
        ).strip()

        try:
            index = int(choice)

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


def choose_source_type() -> str:
    """Choose one of the simple evidence categories."""

    options = {
        "1": "computational",
        "2": "experimental",
        "3": "literature",
        "4": "note",
    }

    print("\nEvidence type")
    print("-" * 30)
    print("1. Computational")
    print("2. Experimental")
    print("3. Literature")
    print("4. Note")

    while True:

        choice = input(
            "\nChoose type: "
        ).strip()

        if choice in options:
            return options[
                choice
            ]

        print(
            "Choose 1, 2, 3, or 4."
        )


def collect_files() -> list[str]:
    """Collect existing evidence files."""

    files: list[str] = []

    print(
        "\nAttach files one at a time."
    )

    print(
        "Press Enter with no path when finished."
    )

    while True:

        path = input(
            "File path: "
        ).strip()

        if not path:
            break

        file_path = Path(
            path
        ).expanduser()

        if not file_path.exists():

            print(
                "File not found."
            )

            continue

        if not file_path.is_file():

            print(
                "Path is not a file."
            )

            continue

        print(
            f"Found: {file_path}"
        )

        files.append(
            str(file_path)
        )

    return files


def main() -> None:
    """Attach external scientific evidence."""

    project = DesignProject.load(
        name="GB1 Human-Guided Design",
        root_dir=PROJECT_DIR,
    )

    design = choose_design(
        project
    )

    print(
        "\nSelected:"
    )

    print(
        "  "
        + project.archive.get_lineage_label(
            design.id
        )
    )

    source_type = choose_source_type()

    source_name = input(
        "\nTechnique / source: "
    ).strip()

    if not source_name:
        source_name = source_type

    summary = input(
        "Short summary: "
    ).strip()

    notes = input(
        "Notes (optional): "
    ).strip()

    files = collect_files()

    evidence = add_external_evidence(
        archive=project.archive,
        design_id=design.id,
        source_type=source_type,
        source_name=source_name,
        summary=summary,
        files=files,
        notes=notes or None,
        project_root=project.root_dir,
        copy_files=True,
    )

    project.save()

    print(
        "\nEvidence added."
    )

    print(
        f"Evidence ID: {evidence.id}"
    )

    print(
        "Design: "
        + project.archive.get_lineage_label(
            design.id
        )
    )

    print(
        f"Type: {evidence.source_type}"
    )

    print(
        f"Source: {evidence.source_name}"
    )

    if evidence.file_paths:

        print(
            "\nStored files:"
        )

        for path in evidence.file_paths:

            print(
                f"  {path}"
            )

if __name__ == "__main__":
    main()