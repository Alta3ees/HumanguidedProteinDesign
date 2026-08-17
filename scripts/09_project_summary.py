from pathlib import Path

from human_protein_design.archive import (
    DesignProject,
    export_project_summary,
)


PROJECT_DIR = Path(
    "data/projects/gb1_design"
)
SUMMARY_PATH = (
    PROJECT_DIR
    / "PROJECT_SUMMARY.md"
)

def format_float(
    value,
) -> str:
    """Format floats for human-readable output."""

    if isinstance(
        value,
        float,
    ):
        return f"{value:.2f}"

    return str(
        value
    )


def get_latest_rosetta_entry(
    project,
    design_id: str,
):
    """Return the latest PyRosetta evidence entry."""

    entries = (
        project.archive.get_design_evidence(
            design_id
        )
    )

    rosetta_entries = [
        entry
        for entry in entries
        if (
            entry.source_type
            == "computational"
            and entry.source_name.lower()
            == "pyrosetta"
        )
    ]

    if not rosetta_entries:
        return None

    return rosetta_entries[-1]


def summarize_design(
    project,
    design,
) -> dict:
    """Build a compact summary for one design."""

    archive = project.archive

    latest_decision = (
        archive.get_latest_decision(
            design.id
        )
    )

    evidence = (
        archive.get_design_evidence(
            design.id
        )
    )

    evidence_counts = {
        "computational": 0,
        "experimental": 0,
        "literature": 0,
        "note": 0,
    }

    methods: list[str] = []

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

        if (
            entry.source_name
            not in methods
        ):
            methods.append(
                entry.source_name
            )

    rosetta = (
        get_latest_rosetta_entry(
            project,
            design.id,
        )
    )

    delta_score = None
    mutant_score = None

    if rosetta is not None:

        delta_score = (
            rosetta.data.get(
                "delta_score"
            )
        )

        mutant_score = (
            rosetta.data.get(
                "mutant_score"
            )
        )

    return {
        "id": design.id,
        "name": (
            archive.get_design_label(
                design.id
            )
        ),
        "lineage": (
            archive.get_lineage_label(
                design.id
            )
        ),
        "status": design.status,
        "decision": (
            latest_decision.outcome
            if latest_decision
            else "none"
        ),
        "delta_score": delta_score,
        "mutant_score": mutant_score,
        "evidence_counts": evidence_counts,
        "methods": methods,
        "evidence_total": len(
            evidence
        ),
    }


def print_overview(
    summaries: list[dict],
) -> None:
    """Print project-wide design overview."""

    print(
        "\nPROJECT OVERVIEW"
    )
    print(
        "=" * 100
    )

    header = (
        f"{'Design':<20}"
        f"{'Decision':<12}"
        f"{'Status':<16}"
        f"{'ΔScore':>10}"
        f"{'Evidence':>10}"
        f"  Methods"
    )

    print(
        header
    )
    print(
        "-" * 100
    )

    for summary in summaries:

        delta = (
            f"{summary['delta_score']:+.2f}"
            if isinstance(
                summary["delta_score"],
                (int, float),
            )
            else "-"
        )

        methods = (
            ", ".join(
                summary["methods"]
            )
            if summary["methods"]
            else "-"
        )

        print(
            f"{summary['name']:<20}"
            f"{summary['decision']:<12}"
            f"{summary['status']:<16}"
            f"{delta:>10}"
            f"{summary['evidence_total']:>10}"
            f"  {methods}"
        )


def print_branch_details(
    summaries: list[dict],
) -> None:
    """Print lineage and evidence details."""

    print(
        "\nDESIGN DETAILS"
    )
    print(
        "=" * 100
    )

    for summary in summaries:

        print(
            f"\n{summary['name']}"
        )

        print(
            "-" * 100
        )

        print(
            f"Lineage:  "
            f"{summary['lineage']}"
        )

        print(
            f"Decision: "
            f"{summary['decision']}"
        )

        print(
            f"Status:   "
            f"{summary['status']}"
        )

        if isinstance(
            summary["delta_score"],
            (int, float),
        ):

            print(
                f"ΔScore:   "
                f"{summary['delta_score']:+.2f} REU"
            )

        if isinstance(
            summary["mutant_score"],
            (int, float),
        ):

            print(
                f"Score:    "
                f"{summary['mutant_score']:.2f} REU"
            )

        counts = (
            summary[
                "evidence_counts"
            ]
        )

        print(
            "Evidence:"
        )

        any_evidence = False

        for category, count in (
            counts.items()
        ):

            if count == 0:
                continue

            any_evidence = True

            print(
                f"  "
                f"{category:<15}"
                f"{count}"
            )

        if not any_evidence:

            print(
                "  none"
            )

        if summary["methods"]:

            print(
                "Methods:  "
                + ", ".join(
                    summary["methods"]
                )
            )


def print_project_statistics(
    project,
    summaries: list[dict],
) -> None:
    """Print basic project statistics."""

    accepted = sum(
        summary["decision"]
        == "accepted"
        for summary in summaries
    )

    rejected = sum(
        summary["decision"]
        == "rejected"
        for summary in summaries
    )

    undecided = sum(
        summary["decision"]
        == "none"
        for summary in summaries
    )

    computational = 0
    experimental = 0
    literature = 0
    notes = 0

    for summary in summaries:

        counts = (
            summary[
                "evidence_counts"
            ]
        )

        computational += (
            counts.get(
                "computational",
                0,
            )
        )

        experimental += (
            counts.get(
                "experimental",
                0,
            )
        )

        literature += (
            counts.get(
                "literature",
                0,
            )
        )

        notes += (
            counts.get(
                "note",
                0,
            )
        )

    print(
        "\nPROJECT STATISTICS"
    )
    print(
        "=" * 100
    )

    print(
        f"Designs:              "
        f"{len(summaries)}"
    )

    print(
        f"Accepted:             "
        f"{accepted}"
    )

    print(
        f"Rejected:             "
        f"{rejected}"
    )

    print(
        f"No decision:          "
        f"{undecided}"
    )

    print(
        f"Computational entries:"
        f" {computational}"
    )

    print(
        f"Experimental entries: "
        f"{experimental}"
    )

    print(
        f"Literature entries:   "
        f"{literature}"
    )

    print(
        f"Notes:                "
        f"{notes}"
    )


def print_evidence_gaps(
    summaries: list[dict],
) -> None:
    """
    Highlight designs with limited evidence.

    This does not judge whether a design is good or bad.
    """

    print(
        "\nEVIDENCE GAPS"
    )
    print(
        "=" * 100
    )

    found_gap = False

    for summary in summaries:

        counts = (
            summary[
                "evidence_counts"
            ]
        )

        missing = []

        if (
            counts.get(
                "computational",
                0,
            )
            == 0
        ):
            missing.append(
                "computational"
            )

        if (
            counts.get(
                "experimental",
                0,
            )
            == 0
        ):
            missing.append(
                "experimental"
            )

        if not missing:
            continue

        found_gap = True

        print(
            f"{summary['name']:<20}"
            f"missing: "
            f"{', '.join(missing)}"
        )

    if not found_gap:

        print(
            "No basic computational/"
            "experimental evidence gaps."
        )


def main() -> None:
    """Print a project-wide scientific summary."""

    project = DesignProject.load(
        name="GB1 Human-Guided Design",
        root_dir=PROJECT_DIR,
    )

    designs = sorted(
        project.archive.designs.values(),
        key=lambda design: (
            design.created_at
        ),
    )

    if not designs:

        print(
            "Project contains no designs."
        )
        return

    summaries = [
        summarize_design(
            project,
            design,
        )
        for design in designs
    ]

    print(
        "\nGB1 HUMAN-GUIDED DESIGN"
    )
    print(
        "=" * 100
    )

    print_project_statistics(
        project,
        summaries,
    )

    print_overview(
        summaries
    )

    print_branch_details(
        summaries
    )

    print_evidence_gaps(
        summaries
    )

    summary_path = export_project_summary(
        archive=project.archive,
        output_path=SUMMARY_PATH,
        project_name=project.name,
    )

    print(
        "\nProject summary saved to:"
    )

    print(
        f"{summary_path}"
    )

if __name__ == "__main__":
    main()