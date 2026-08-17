"""Human-readable project summary export."""

from __future__ import annotations

from pathlib import Path

from human_protein_design.archive.store import (
    DesignArchive,
)


def format_date(
    timestamp: str,
) -> str:
    """Return YYYY-MM-DD from an ISO timestamp."""

    return timestamp.split(
        "T",
        1,
    )[0]


def get_latest_rosetta(
    archive: DesignArchive,
    design_id: str,
):
    """Return latest PyRosetta evidence."""

    entries = archive.get_design_evidence(
        design_id
    )

    matches = [
        entry
        for entry in entries
        if (
            entry.source_type == "computational"
            and entry.source_name.lower()
            == "pyrosetta"
        )
    ]

    if not matches:
        return None

    return matches[-1]


def export_project_summary(
    archive: DesignArchive,
    output_path: str | Path,
    project_name: str,
) -> Path:
    """Export a readable Markdown project dashboard."""

    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    designs = sorted(
        archive.designs.values(),
        key=lambda design: design.created_at,
    )

    lines: list[str] = []

    lines.extend(
        [
            f"# {project_name}",
            "",
            "Human-readable summary generated from "
            "`design_archive.json`.",
            "",
        ]
    )

    # ============================================================
    # Project statistics
    # ============================================================

    accepted = 0
    rejected = 0
    undecided = 0

    for design in designs:

        decision = archive.get_latest_decision(
            design.id
        )

        if decision is None:
            undecided += 1

        elif decision.outcome == "accepted":
            accepted += 1

        elif decision.outcome == "rejected":
            rejected += 1

    lines.extend(
        [
            "## Project overview",
            "",
            f"- Designs: **{len(designs)}**",
            f"- Accepted: **{accepted}**",
            f"- Rejected: **{rejected}**",
            f"- No decision: **{undecided}**",
            "",
        ]
    )

    # ============================================================
    # Design table
    # ============================================================

    lines.extend(
        [
            "## Designs",
            "",
            "| Design | Lineage | Decision | Status | ΔScore | Evidence |",
            "|---|---|---|---|---:|---:|",
        ]
    )

    for design in designs:

        label = archive.get_design_label(
            design.id
        )

        lineage = archive.get_lineage_label(
            design.id
        )

        decision = archive.get_latest_decision(
            design.id
        )

        decision_text = (
            decision.outcome
            if decision is not None
            else "—"
        )

        evidence = archive.get_design_evidence(
            design.id
        )

        rosetta = get_latest_rosetta(
            archive,
            design.id,
        )

        delta_text = "—"

        if rosetta is not None:

            delta = rosetta.data.get(
                "delta_score"
            )

            if isinstance(
                delta,
                (int, float),
            ):
                delta_text = (
                    f"{delta:+.2f}"
                )

        lines.append(
            f"| {label} "
            f"| {lineage} "
            f"| {decision_text} "
            f"| {design.status} "
            f"| {delta_text} "
            f"| {len(evidence)} |"
        )

    # ============================================================
    # Detailed design records
    # ============================================================

    lines.extend(
        [
            "",
            "## Design records",
            "",
        ]
    )

    for design in designs:

        label = archive.get_design_label(
            design.id
        )

        lineage = archive.get_lineage_label(
            design.id
        )

        decisions = archive.get_design_decisions(
            design.id
        )

        evidence = archive.get_design_evidence(
            design.id
        )

        lines.extend(
            [
                f"### {label}",
                "",
                f"**Lineage:** {lineage}",
                "",
                f"**Status:** {design.status}",
                "",
                f"**Created:** "
                f"{format_date(design.created_at)}",
                "",
            ]
        )

        if design.structure_path:

            lines.extend(
                [
                    "**Structure:**",
                    "",
                    f"`{design.structure_path}`",
                    "",
                ]
            )

        # --------------------------------------------------------
        # Decisions
        # --------------------------------------------------------

        lines.append(
            "**Decision history**"
        )

        lines.append(
            ""
        )

        if not decisions:

            lines.append(
                "- No decisions recorded."
            )

        for decision in decisions:

            lines.append(
                f"- **{decision.outcome.title()}** "
                f"({format_date(decision.created_at)})"
            )

            if decision.hypothesis:

                lines.append(
                    f"  - Hypothesis: "
                    f"{decision.hypothesis}"
                )

            if decision.objective:

                lines.append(
                    f"  - Objective: "
                    f"{decision.objective}"
                )

            if decision.rationale:

                lines.append(
                    f"  - Rationale: "
                    f"{decision.rationale}"
                )

        lines.append(
            ""
        )

        # --------------------------------------------------------
        # Evidence
        # --------------------------------------------------------

        lines.append(
            "**Evidence**"
        )

        lines.append(
            ""
        )

        if not evidence:

            lines.append(
                "- No evidence recorded."
            )

        for entry in evidence:

            lines.append(
                f"- **{entry.source_name}** "
                f"— {entry.source_type} "
                f"({format_date(entry.created_at)})"
            )

            lines.append(
                f"  - {entry.summary}"
            )

            if entry.notes:

                lines.append(
                    f"  - Notes: {entry.notes}"
                )

            if entry.file_paths:

                lines.append(
                    "  - Files:"
                )

                for path in entry.file_paths:

                    lines.append(
                        f"    - `{path}`"
                    )

        lines.extend(
            [
                "",
                "---",
                "",
            ]
        )

    output_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    return output_path