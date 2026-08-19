from pathlib import Path

from human_protein_design.archive import DesignProject
from human_protein_design.cli import choose_item, choose_project


def design_label(project: DesignProject, design) -> str:
    latest = project.archive.get_latest_decision(design.id)
    decision = latest.outcome if latest else "none"
    return (
        f"{project.archive.get_lineage_label(design.id)} "
        f"status={design.status} decision={decision}"
    )


def print_design_header(project: DesignProject, design) -> None:
    archive = project.archive
    print("\nDESIGN REVIEW")
    print("=" * 70)
    print(f"\nDesign ID:\n  {design.id}")
    print(f"\nLineage:\n  {archive.get_lineage_label(design.id)}")

    mutations = archive.get_lineage_mutations(design.id)
    print("\nAccumulated mutations:")
    print("  " + (", ".join(mutations) if mutations else "None (root design)"))

    print(f"\nCurrent status:\n  {design.status}")
    print(f"\nCreated:\n  {design.created_at}")
    print("\nSequence:")
    print(f"  {design.sequence if design.sequence else 'No sequence attached.'}")

    structures = archive.get_design_structures(design.id)
    print("\nStructures:")
    if structures:
        for structure in structures:
            print(
                f"  {structure.id[:12]}  source={structure.source}  "
                f"method={structure.method or '-'}  path={structure.structure_path}"
            )
    elif design.structure_path:
        print(f"  {design.structure_path} (legacy structure path)")
    else:
        print("  No structure attached.")


def print_decisions(project: DesignProject, design) -> None:
    decisions = project.archive.get_design_decisions(design.id)
    print("\nDECISION HISTORY")
    print("=" * 70)
    if not decisions:
        print("\nNo decisions recorded.")
        return

    for index, decision in enumerate(decisions, start=1):
        print(f"\nDecision {index}")
        print("-" * 70)
        print(f"Date:       {decision.created_at}")
        print(f"Outcome:    {decision.outcome}")
        if decision.hypothesis:
            print(f"Hypothesis: {decision.hypothesis}")
        if decision.objective:
            print(f"Objective:  {decision.objective}")
        if decision.rationale:
            print(f"Rationale:  {decision.rationale}")
        if decision.user_note:
            print(f"User note:  {decision.user_note}")
        if decision.program_comment:
            print(f"Program:    {decision.program_comment}")


def print_evidence(project: DesignProject, design) -> None:
    entries = project.archive.get_design_evidence(design.id)
    print("\nEVIDENCE")
    print("=" * 70)
    if not entries:
        print("\nNo evidence recorded.")
        return

    grouped: dict[str, list] = {}
    for entry in entries:
        grouped.setdefault(entry.source_type, []).append(entry)

    for source_type in ("computational", "experimental", "literature", "note"):
        source_entries = grouped.get(source_type, [])
        if not source_entries:
            continue
        print(f"\n{source_type.upper()}")
        print("-" * 70)
        for index, entry in enumerate(source_entries, start=1):
            print(f"\n[{index}] {entry.source_name}")
            print(f"Date: {entry.created_at}")
            print(f"Summary: {entry.summary}")
            if entry.data:
                print("Data:")
                for key, value in entry.data.items():
                    print(f"  {key}: {value}")
            if entry.notes:
                print(f"Notes: {entry.notes}")
            if entry.file_paths:
                print("Files:")
                for stored in entry.file_paths:
                    path = Path(stored)
                    resolved = path if path.is_absolute() else project.root_dir / path
                    state = "found" if resolved.exists() else "missing"
                    print(f"  [{state}] {stored}")
            if entry.references:
                print("References:")
                for reference in entry.references:
                    print(f"  {reference}")


def print_summary(project: DesignProject, design) -> None:
    archive = project.archive
    decisions = archive.get_design_decisions(design.id)
    evidence = archive.get_design_evidence(design.id)
    latest = archive.get_latest_decision(design.id)
    counts = archive.get_design_evidence_counts(design.id)

    print("\nSUMMARY")
    print("=" * 70)
    print(f"\nLineage: {archive.get_lineage_label(design.id)}")
    print(f"Status: {design.status}")
    print(f"Latest decision: {latest.outcome if latest else 'none'}")
    print(f"Decisions recorded: {len(decisions)}")
    print(f"Evidence entries: {len(evidence)}")
    print(f"Structure models: {len(archive.get_design_structures(design.id))}")
    if any(counts.values()):
        print("\nEvidence breakdown:")
        for source_type, count in counts.items():
            if count:
                print(f"  {source_type:<15}{count}")


def main() -> None:
    """Review the complete scientific record for one design."""
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

    print_design_header(project, design)
    print_decisions(project, design)
    print_evidence(project, design)
    print_summary(project, design)


if __name__ == "__main__":
    main()
