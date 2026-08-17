from pathlib import Path

from human_protein_design.archive import (
    DesignProject,
)


PROJECT_DIR = Path(
    "data/projects/gb1_design"
)


def decision_symbol(
    outcome: str | None,
) -> str:
    """Return a compact decision symbol."""

    symbols = {
        "accepted": "✓",
        "rejected": "✗",
        "deferred": "?",
        None: "•",
    }

    return symbols.get(
        outcome,
        "•",
    )


def format_evidence(
    counts: dict[str, int],
) -> str:
    """Format non-zero evidence counts."""

    labels = {
        "computational": "comp",
        "experimental": "exp",
        "literature": "lit",
        "note": "notes",
    }

    parts = []

    for category, count in counts.items():

        if count == 0:
            continue

        label = labels.get(
            category,
            category,
        )

        parts.append(
            f"{label}:{count}"
        )

    if not parts:
        return ""

    return (
        " ["
        + ", ".join(parts)
        + "]"
    )


def print_branch(
    project,
    design_id: str,
    prefix: str = "",
    is_last: bool = True,
    is_root: bool = False,
) -> None:
    """Recursively print a design-tree branch."""

    archive = project.archive

    design = archive.get_design(
        design_id
    )

    label = archive.get_design_label(
        design_id
    )

    outcome = archive.get_decision_outcome(
        design_id
    )

    symbol = decision_symbol(
        outcome
    )

    delta_score = (
        archive.get_rosetta_delta_score(
            design_id
        )
    )

    evidence_counts = (
        archive.get_design_evidence_counts(
            design_id
        )
    )

    evidence_text = format_evidence(
        evidence_counts
    )

    score_text = ""

    if delta_score is not None:
        score_text = (
            f" Δ{delta_score:+.2f}"
        )

    status_text = (
        f" ({design.status})"
    )

    if is_root:

        print(
            f"{symbol} {label}"
            f"{status_text}"
            f"{score_text}"
            f"{evidence_text}"
        )

    else:

        connector = (
            "└── "
            if is_last
            else "├── "
        )

        print(
            f"{prefix}"
            f"{connector}"
            f"{symbol} {label}"
            f"{status_text}"
            f"{score_text}"
            f"{evidence_text}"
        )

    children = archive.get_children(
        design_id
    )

    children = sorted(
        children,
        key=lambda child: child.created_at,
    )

    if is_root:
        child_prefix = ""
    else:
        child_prefix = (
            prefix
            + (
                "    "
                if is_last
                else "│   "
            )
        )

    for index, child in enumerate(
        children
    ):

        child_is_last = (
            index
            == len(children) - 1
        )

        print_branch(
            project=project,
            design_id=child.id,
            prefix=child_prefix,
            is_last=child_is_last,
            is_root=False,
        )


def main() -> None:
    """Print the full design project tree."""

    project = DesignProject.load(
        name="GB1 Human-Guided Design",
        root_dir=PROJECT_DIR,
    )

    roots = (
        project.archive.get_root_designs()
    )

    if not roots:
        print(
            "Project contains no designs."
        )
        return

    print(
        "\nGB1 DESIGN TREE"
    )

    print(
        "=" * 70
    )

    print(
        "\nLegend:"
    )

    print(
        "  ✓ accepted"
    )

    print(
        "  ✗ rejected"
    )

    print(
        "  ? deferred"
    )

    print(
        "  • no decision"
    )

    print()

    for root in roots:

        print_branch(
            project=project,
            design_id=root.id,
            is_root=True,
        )

        print()


if __name__ == "__main__":
    main()