from human_protein_design.archive import (
    DesignProject,
    export_project_summary,
)
from human_protein_design.cli import choose_project


def get_latest_rosetta_entry(project, design_id: str):
    entries = project.archive.get_design_evidence(design_id)
    rosetta_entries = [
        entry
        for entry in entries
        if entry.source_type == "computational"
        and entry.source_name.lower() == "pyrosetta"
    ]
    return rosetta_entries[-1] if rosetta_entries else None


def summarize_design(project, design) -> dict:
    archive = project.archive
    latest_decision = archive.get_latest_decision(design.id)
    evidence = archive.get_design_evidence(design.id)
    evidence_counts = {
        "computational": 0,
        "experimental": 0,
        "literature": 0,
        "note": 0,
    }
    methods: list[str] = []
    for entry in evidence:
        evidence_counts[entry.source_type] = evidence_counts.get(entry.source_type, 0) + 1
        if entry.source_name not in methods:
            methods.append(entry.source_name)

    rosetta = get_latest_rosetta_entry(project, design.id)
    delta_score = rosetta.data.get("delta_score") if rosetta else None
    mutant_score = rosetta.data.get("mutant_score") if rosetta else None

    return {
        "id": design.id,
        "name": archive.get_design_label(design.id),
        "lineage": archive.get_lineage_label(design.id),
        "status": design.status,
        "decision": latest_decision.outcome if latest_decision else "none",
        "delta_score": delta_score,
        "mutant_score": mutant_score,
        "evidence_counts": evidence_counts,
        "methods": methods,
        "evidence_total": len(evidence),
        "structure_total": len(archive.get_design_structures(design.id)),
    }


def print_overview(summaries: list[dict]) -> None:
    print("\nPROJECT OVERVIEW")
    print("=" * 110)
    print(
        f"{'Design':<20}{'Decision':<12}{'Status':<16}"
        f"{'ΔScore':>10}{'Evidence':>10}{'Struct':>8}  Methods"
    )
    print("-" * 110)
    for summary in summaries:
        delta = (
            f"{summary['delta_score']:+.2f}"
            if isinstance(summary["delta_score"], (int, float))
            else "-"
        )
        methods = ", ".join(summary["methods"]) if summary["methods"] else "-"
        print(
            f"{summary['name']:<20}{summary['decision']:<12}"
            f"{summary['status']:<16}{delta:>10}"
            f"{summary['evidence_total']:>10}{summary['structure_total']:>8}  {methods}"
        )


def print_branch_details(summaries: list[dict]) -> None:
    print("\nDESIGN DETAILS")
    print("=" * 100)
    for summary in summaries:
        print(f"\n{summary['name']}")
        print("-" * 100)
        print(f"Lineage:   {summary['lineage']}")
        print(f"Decision:  {summary['decision']}")
        print(f"Status:    {summary['status']}")
        print(f"Structures:{summary['structure_total']:>3}")
        if isinstance(summary["delta_score"], (int, float)):
            print(f"ΔScore:    {summary['delta_score']:+.2f} REU")
        if isinstance(summary["mutant_score"], (int, float)):
            print(f"Score:     {summary['mutant_score']:.2f} REU")

        print("Evidence:")
        present = False
        for category, count in summary["evidence_counts"].items():
            if count:
                present = True
                print(f"  {category:<15}{count}")
        if not present:
            print("  none")
        if summary["methods"]:
            print("Methods:   " + ", ".join(summary["methods"]))


def print_project_statistics(project, summaries: list[dict]) -> None:
    accepted = sum(summary["decision"] == "accepted" for summary in summaries)
    rejected = sum(summary["decision"] == "rejected" for summary in summaries)
    deferred = sum(summary["decision"] == "deferred" for summary in summaries)
    undecided = sum(summary["decision"] == "none" for summary in summaries)
    totals = {"computational": 0, "experimental": 0, "literature": 0, "note": 0}
    for summary in summaries:
        for category in totals:
            totals[category] += summary["evidence_counts"].get(category, 0)

    print("\nPROJECT STATISTICS")
    print("=" * 100)
    print(f"Designs:              {len(summaries)}")
    print(f"Structure models:     {len(project.archive.structures)}")
    print(f"Accepted:             {accepted}")
    print(f"Rejected:             {rejected}")
    print(f"Deferred:             {deferred}")
    print(f"No decision:          {undecided}")
    print(f"Computational entries: {totals['computational']}")
    print(f"Experimental entries:  {totals['experimental']}")
    print(f"Literature entries:    {totals['literature']}")
    print(f"Notes:                 {totals['note']}")


def print_evidence_gaps(summaries: list[dict]) -> None:
    print("\nEVIDENCE GAPS")
    print("=" * 100)
    found_gap = False
    for summary in summaries:
        counts = summary["evidence_counts"]
        missing = []
        if counts.get("computational", 0) == 0:
            missing.append("computational")
        if counts.get("experimental", 0) == 0:
            missing.append("experimental")
        if missing:
            found_gap = True
            print(f"{summary['name']:<20}missing: {', '.join(missing)}")
    if not found_gap:
        print("No basic computational/experimental evidence gaps.")


def main() -> None:
    """Print and save a project-wide scientific summary."""
    project_dir = choose_project()
    project = DesignProject.load(name=project_dir.name, root_dir=project_dir)
    designs = sorted(project.archive.designs.values(), key=lambda design: design.created_at)

    if not designs:
        print("Project contains no designs.")
        return

    summaries = [summarize_design(project, design) for design in designs]
    print(f"\n{project.name.upper()}")
    print("=" * 100)
    print_project_statistics(project, summaries)
    print_overview(summaries)
    print_branch_details(summaries)
    print_evidence_gaps(summaries)

    summary_path = export_project_summary(
        archive=project.archive,
        output_path=project.root_dir / "PROJECT_SUMMARY.md",
        project_name=project.name,
    )
    print("\nProject summary saved to:")
    print(summary_path)


if __name__ == "__main__":
    main()
