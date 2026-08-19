from pathlib import Path

from human_protein_design.archive import (
    DesignProject,
    add_external_evidence,
)
from human_protein_design.cli import (
    ask_choice,
    ask_text,
    choose_files,
    choose_item,
    choose_project,
)


def design_label(project: DesignProject, design) -> str:
    latest_decision = project.archive.get_latest_decision(design.id)
    decision_text = latest_decision.outcome if latest_decision is not None else "none"
    return (
        f"{project.archive.get_lineage_label(design.id)} "
        f"status={design.status} decision={decision_text}"
    )


def main() -> None:
    """Attach external scientific evidence."""
    project_dir = choose_project()
    project = DesignProject.load(name=project_dir.name, root_dir=project_dir)

    designs = list(project.archive.designs.values())
    if not designs:
        raise SystemExit("Project contains no designs.")

    design = choose_item(
        designs,
        "Choose design",
        label=lambda item: design_label(project, item),
    )
    assert design is not None

    print("\nEvidence type:\n  1. Computational\n  2. Experimental\n  3. Literature\n  4. Note")
    source_type = ask_choice(
        "Choose type",
        {
            "1": "computational",
            "2": "experimental",
            "3": "literature",
            "4": "note",
        },
    )

    source_name = ask_text("Technique / source", required=False) or source_type
    summary = ask_text("Short summary")
    notes = ask_text("Notes", required=False) or None
    files = choose_files(
        Path.cwd(),
        "Select evidence file",
    )

    evidence = add_external_evidence(
        archive=project.archive,
        design_id=design.id,
        source_type=source_type,
        source_name=source_name,
        summary=summary,
        files=[str(path) for path in files],
        notes=notes,
        project_root=project.root_dir,
        copy_files=True,
    )

    project.save()

    print("\nEvidence added.")
    print(f"Evidence ID: {evidence.id}")
    print("Design: " + project.archive.get_lineage_label(design.id))
    print(f"Type: {evidence.source_type}")
    print(f"Source: {evidence.source_name}")

    if evidence.file_paths:
        print("\nStored files:")
        for path in evidence.file_paths:
            print(f"  {path}")


if __name__ == "__main__":
    main()
