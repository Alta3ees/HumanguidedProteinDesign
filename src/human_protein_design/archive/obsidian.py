"""Obsidian-friendly Markdown export."""

from __future__ import annotations

from pathlib import Path

from human_protein_design.archive.store import (
    DesignArchive,
)


def safe_filename(
    text: str,
) -> str:
    """Return a safe Markdown filename."""

    safe = (
        text.strip()
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )

    return safe or "design"


def design_note_filename(
    archive: DesignArchive,
    design_id: str,
) -> str:
    """Return a stable Markdown filename for a design."""

    design = archive.get_design(
        design_id
    )

    label = archive.get_design_label(
        design_id
    )

    # Keep ID fragment to avoid collisions between
    # designs that share the same human-readable name.
    short_id = design.id.split(
        "_",
        1,
    )[-1][:8]

    return (
        f"{safe_filename(label)}"
        f"__{short_id}.md"
    )


def export_design_note(
    archive: DesignArchive,
    design_id: str,
    output_dir: str | Path,
) -> Path:
    """Export one design as an Obsidian Markdown note."""

    output_dir = Path(
        output_dir
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    design = archive.get_design(
        design_id
    )

    label = archive.get_design_label(
        design_id
    )

    decisions = (
        archive.get_design_decisions(
            design_id
        )
    )

    evidence = (
        archive.get_design_evidence(
            design_id
        )
    )

    children = archive.get_children(
        design_id
    )

    lineage = archive.get_lineage(
        design_id
    )

    lines: list[str] = []

    # --------------------------------
    # YAML frontmatter
    # --------------------------------

    lines.extend(
        [
            "---",
            f'design_id: "{design.id}"',
            f'name: "{label}"',
            f'status: "{design.status}"',
            f'created_at: "{design.created_at}"',
        ]
    )

    latest = archive.get_latest_decision(
        design_id
    )

    if latest is not None:
        lines.append(
            f'latest_decision: "{latest.outcome}"'
        )

    lines.extend(
        [
            "tags:",
            "  - protein-design",
            "  - human-guided-design",
            "---",
            "",
            f"# {label}",
            "",
        ]
    )

    # --------------------------------
    # Lineage
    # --------------------------------

    lines.append(
        "## Lineage"
    )

    lines.append(
        ""
    )

    lineage_links = []

    for lineage_design in lineage:

        lineage_file = (
            design_note_filename(
                archive,
                lineage_design.id,
            )
        )

        lineage_name = archive.get_design_label(
            lineage_design.id
        )

        lineage_links.append(
            f"[[{Path(lineage_file).stem}"
            f"|{lineage_name}]]"
        )

    lines.append(
        " → ".join(
            lineage_links
        )
    )

    # --------------------------------
    # Sequence
    # --------------------------------

    formatted_sequence = (
        format_sequence_with_mutations(
            archive,
            design_id,
        )
    )

    lines.extend(
        [
            "",
            "## Sequence",
            "",
            formatted_sequence,
        ]
    )

    # --------------------------------
    # Structure
    # --------------------------------

    lines.extend(
        [
            "",
            "## Structure",
            "",
        ]
    )

    if design.structure_path:
        lines.append(
            f"`{design.structure_path}`"
        )
    else:
        lines.append(
            "No structure attached."
        )

    # --------------------------------
    # Decisions
    # --------------------------------

    lines.extend(
        [
            "",
            "## Decision history",
            "",
        ]
    )

    if not decisions:

        lines.append(
            "No decisions recorded."
        )

    for decision in decisions:

        lines.append(
            f"### {decision.outcome.title()}"
        )

        lines.append(
            ""
        )

        lines.append(
            f"- Date: {format_date(decision.created_at)}"
        )

        if decision.hypothesis:
            lines.append(
                f"- Hypothesis: "
                f"{decision.hypothesis}"
            )

        if decision.objective:
            lines.append(
                f"- Objective: "
                f"{decision.objective}"
            )

        if decision.rationale:
            lines.append(
                f"- Rationale: "
                f"{decision.rationale}"
            )

        if decision.user_note:
            lines.append(
                f"- User note: "
                f"{decision.user_note}"
            )

        lines.append(
            ""
        )

    # --------------------------------
    # Evidence
    # --------------------------------

    lines.extend(
        [
            "## Evidence",
            "",
        ]
    )

    if not evidence:

        lines.append(
            "No evidence recorded."
        )

    for entry in evidence:

        lines.append(
            f"### {entry.source_name}"
        )

        lines.append(
            ""
        )

        lines.append(
            f"- Type: {entry.source_type}"
        )

        lines.append(
            f"- Date: {format_date(entry.created_at)}"
        )

        lines.append(
            f"- Summary: {entry.summary}"
        )

        if entry.notes:

            lines.append(
                f"- Notes: {entry.notes}"
            )

        if entry.data:

            lines.append(
                "- Data:"
            )

            lines.extend(
                format_data_value(
                    entry.data,
                    indent=1,
                )
            )

        if entry.file_paths:

            lines.append(
                "- Files:"
            )

            for path in entry.file_paths:

                lines.append(
                    f"  - `{path}`"
                )

        if entry.references:

            lines.append(
                "- References:"
            )

            for reference in (
                entry.references
            ):

                lines.append(
                    f"  - {reference}"
                )

        lines.append(
            ""
        )

    # --------------------------------
    # Children
    # --------------------------------

    lines.extend(
        [
            "## Child designs",
            "",
        ]
    )

    if not children:

        lines.append(
            "No child designs."
        )

    for child in children:

        child_file = (
            design_note_filename(
                archive,
                child.id,
            )
        )

        child_label = (
            archive.get_design_label(
                child.id
            )
        )

        lines.append(
            f"- [[{Path(child_file).stem}"
            f"|{child_label}]]"
        )

    output_path = (
        output_dir
        / design_note_filename(
            archive,
            design_id,
        )
    )

    output_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    return output_path


def export_obsidian_vault(
    archive: DesignArchive,
    output_dir: str | Path,
) -> None:
    """Export all designs as linked Markdown notes."""

    output_dir = Path(
        output_dir
    )

    designs_dir = (
        output_dir
        / "Designs"
    )

    designs_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for design in archive.designs.values():

        export_design_note(
            archive=archive,
            design_id=design.id,
            output_dir=designs_dir,
        )

def format_data_value(
    value,
    indent: int = 0,
) -> list[str]:
    """Format nested evidence data as Markdown."""

    lines: list[str] = []

    if isinstance(value, dict):

        for key, item in value.items():

            if isinstance(
                item,
                (dict, list),
            ):
                lines.append(
                    f"{'  ' * indent}- {key}:"
                )

                lines.extend(
                    format_data_value(
                        item,
                        indent + 1,
                    )
                )

            else:

                if isinstance(item, float):
                    text = f"{item:.2f}"
                else:
                    text = str(item)

                lines.append(
                    f"{'  ' * indent}- "
                    f"{key}: {text}"
                )

    elif isinstance(value, list):

        for item in value:

            if isinstance(
                item,
                (dict, list),
            ):
                lines.extend(
                    format_data_value(
                        item,
                        indent,
                    )
                )
            else:

                if isinstance(item, float):
                    text = f"{item:.2f}"
                else:
                    text = str(item)

                lines.append(
                    f"{'  ' * indent}- {text}"
                )

    else:

        if isinstance(value, float):
            text = f"{value:.2f}"
        else:
            text = str(value)

        lines.append(
            f"{'  ' * indent}- {text}"
        )

    return lines

def format_date(timestamp: str) -> str:
    """Return only the YYYY-MM-DD part of an ISO timestamp."""

    return timestamp.split(
        "T",
        1,
    )[0]

def format_sequence_with_mutations(
    archive: DesignArchive,
    design_id: str,
) -> str:
    """Highlight residues that differ from the root sequence."""

    design = archive.get_design(
        design_id
    )

    lineage = archive.get_lineage(
        design_id
    )

    root = lineage[0]

    root_sequence = root.sequence
    sequence = design.sequence

    formatted: list[str] = []

    for root_aa, design_aa in zip(
        root_sequence,
        sequence,
    ):

        if root_aa != design_aa:

            formatted.append(
                '<span style="color:#4da6ff; '
                'font-weight:bold;">'
                f"{design_aa}"
                "</span>"
            )

        else:

            formatted.append(
                design_aa
            )

    return "".join(
        formatted
    )