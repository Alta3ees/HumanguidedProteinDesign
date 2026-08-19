"""Safe deletion of leaf design nodes from the local scientific archive."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from human_protein_design.archive import DesignProject
from human_protein_design.web.actions import delete_evidence, delete_structure


def _delete_project_local_legacy_structure(project: DesignProject, stored_path: str | None) -> list[str]:
    """Delete a legacy design.structure_path only when it is private to this design."""
    if not stored_path:
        return []

    candidate = Path(stored_path)
    if not candidate.is_absolute():
        candidate = (project.root_dir / candidate).resolve()
    else:
        candidate = candidate.resolve()

    structures_root = project.structures_dir.resolve()
    try:
        candidate.relative_to(structures_root)
    except ValueError:
        return []

    for structure in project.archive.structures.values():
        other = Path(structure.structure_path)
        if not other.is_absolute():
            other = (project.root_dir / other).resolve()
        else:
            other = other.resolve()
        if other == candidate:
            return []

    if not candidate.is_file():
        return []

    candidate.unlink()
    try:
        return [str(candidate.relative_to(project.root_dir.resolve()))]
    except ValueError:
        return [stored_path]


def delete_leaf_design(project: DesignProject, design_id: str) -> dict[str, Any]:
    """Delete one leaf design and data owned directly by that design.

    Descendants are never deleted implicitly. A design with children must be
    pruned from the leaves upward so one mistaken click cannot erase a branch of
    scientific history.
    """
    try:
        design = project.archive.designs[design_id]
    except KeyError as error:
        raise KeyError(f"Unknown design: {design_id}") from error

    children = project.archive.get_children(design_id)
    if children:
        labels = [project.archive.get_design_label(child.id) for child in children]
        raise ValueError(
            "Cannot delete a design that still has child designs. "
            f"Delete its child branch(es) first: {', '.join(labels)}"
        )

    parent_design_id = design.parent_design_id
    deleted_files: list[str] = []

    # Remove registered structures first so their project-local files are
    # cleaned up using the same safety rules as explicit structure deletion.
    for structure in list(project.archive.get_design_structures(design_id)):
        deleted_files.extend(delete_structure(project, structure.id))

    # Legacy v0.3 structure_path values can exist without a StructureModel.
    deleted_files.extend(_delete_project_local_legacy_structure(project, design.structure_path))

    # Evidence directly owned by this design is removed together with its
    # private evidence-directory files. External references and unrelated files
    # remain untouched by delete_evidence().
    evidence_ids = [
        evidence.id
        for evidence in project.archive.evidence.values()
        if evidence.design_id == design_id
    ]
    for evidence_id in evidence_ids:
        deleted_files.extend(delete_evidence(project, evidence_id))

    # Decisions involving the deleted leaf can no longer remain valid archive
    # references. Evidence that has another surviving owner is detached from the
    # deleted decision; decision-only evidence is deleted so we never leave an
    # evidence record with no scientific owner at all.
    decision_ids = [
        decision.id
        for decision in project.archive.decisions.values()
        if decision.candidate_design_id == design_id or decision.parent_design_id == design_id
    ]
    for decision_id in decision_ids:
        decision_only_evidence_ids: list[str] = []
        for evidence in list(project.archive.evidence.values()):
            if evidence.decision_id != decision_id:
                continue
            has_other_owner = any(
                (
                    evidence.design_id,
                    evidence.structure_id,
                    evidence.target_id,
                )
            )
            if not has_other_owner:
                decision_only_evidence_ids.append(evidence.id)
                continue
            evidence.decision_id = None
            evidence.data = dict(evidence.data)
            evidence.data["decision_removed"] = True
            evidence.data["removed_decision_id"] = decision_id

        for evidence_id in decision_only_evidence_ids:
            deleted_files.extend(delete_evidence(project, evidence_id))

        del project.archive.decisions[decision_id]

    del project.archive.designs[design_id]
    project.save()

    return {
        "design_id": design_id,
        "parent_design_id": parent_design_id,
        "deleted_files": sorted(set(deleted_files)),
        "deleted_evidence_count": len(evidence_ids),
        "deleted_decision_count": len(decision_ids),
    }
