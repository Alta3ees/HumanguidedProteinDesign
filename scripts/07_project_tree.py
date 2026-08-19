from human_protein_design.archive import DesignProject
from human_protein_design.cli import choose_project


def decision_symbol(outcome: str | None) -> str:
    return {
        "accepted": "✓",
        "rejected": "✗",
        "deferred": "?",
        None: "•",
    }.get(outcome, "•")


def format_evidence(counts: dict[str, int]) -> str:
    labels = {
        "computational": "comp",
        "experimental": "exp",
        "literature": "lit",
        "note": "notes",
    }
    parts = [f"{labels.get(category, category)}:{count}" for category, count in counts.items() if count]
    return " [" + ", ".join(parts) + "]" if parts else ""


def print_branch(project, design_id: str, prefix: str = "", is_last: bool = True, is_root: bool = False) -> None:
    archive = project.archive
    design = archive.get_design(design_id)
    label = archive.get_design_label(design_id)
    symbol = decision_symbol(archive.get_decision_outcome(design_id))
    delta_score = archive.get_rosetta_delta_score(design_id)
    evidence_text = format_evidence(archive.get_design_evidence_counts(design_id))
    score_text = f" Δ{delta_score:+.2f}" if delta_score is not None else ""
    structures = archive.get_design_structures(design_id)
    structure_text = f" structures:{len(structures)}" if structures else ""
    status_text = f" ({design.status})"

    if is_root:
        print(f"{symbol} {label}{status_text}{score_text}{structure_text}{evidence_text}")
    else:
        connector = "└── " if is_last else "├── "
        print(f"{prefix}{connector}{symbol} {label}{status_text}{score_text}{structure_text}{evidence_text}")

    children = sorted(archive.get_children(design_id), key=lambda child: child.created_at)
    child_prefix = "" if is_root else prefix + ("    " if is_last else "│   ")
    for index, child in enumerate(children):
        print_branch(
            project=project,
            design_id=child.id,
            prefix=child_prefix,
            is_last=index == len(children) - 1,
            is_root=False,
        )


def main() -> None:
    """Print the full design project tree."""
    project_dir = choose_project()
    project = DesignProject.load(name=project_dir.name, root_dir=project_dir)
    roots = project.archive.get_root_designs()

    print(f"\n{project.name} — DESIGN TREE")
    print("=" * 70)
    print("\nLegend: ✓ accepted | ✗ rejected | ? deferred | • no decision\n")

    if not roots:
        print("Project contains no designs.")
        return

    for root in roots:
        print_branch(project=project, design_id=root.id, is_root=True)
        print()


if __name__ == "__main__":
    main()
