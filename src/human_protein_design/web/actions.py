"""Validated archive actions used by the local v0.4 web workspace.

These helpers keep filesystem and provenance rules outside React/FastAPI route
handlers. They deliberately operate on the same archive models as the CLI
scripts so the web UI becomes another interface, not a second data model.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from human_protein_design.archive import (
    Design,
    DesignProject,
    EvidenceEntry,
    ProjectObjective,
    StructureModel,
    Target,
)
from human_protein_design.fasta import normalize_sequence

STRUCTURE_SUFFIXES = {".pdb", ".cif", ".mmcif"}
DESIGN_ORIGINS = {
    "natural_sequence",
    "point_mutation",
    "de_novo",
    "generated_backbone",
    "sequence_design",
    "imported_design",
}
STRUCTURE_SOURCES = {
    "experimental",
    "alphafold",
    "colabfold",
    "rfdiffusion",
    "rosetta",
    "user",
    "other",
}


def make_slug(name: str) -> str:
    """Return a conservative project directory slug."""
    slug = "".join(
        char
        for char in "_".join(name.lower().split())
        if char.isalnum() or char in {"_", "-"}
    ).strip("_-")
    if not slug:
        raise ValueError("Project name does not produce a valid directory name.")
    return slug


def safe_filename(filename: str | None, fallback: str = "file") -> str:
    raw = Path(filename or fallback).name
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("._")
    return safe or fallback


def unique_destination(destination_dir: Path, filename: str) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    candidate = destination_dir / safe_filename(filename)
    if not candidate.exists():
        return candidate
    stem, suffix, counter = candidate.stem, candidate.suffix, 2
    while candidate.exists():
        candidate = destination_dir / f"{stem}_{counter}{suffix}"
        counter += 1
    return candidate


def create_project(
    *,
    projects_root: Path,
    name: str,
    objective: str,
    sequence: str | None = None,
    design_name: str | None = None,
    target_name: str | None = None,
    target_sequence: str | None = None,
) -> DesignProject:
    """Create a local project with optional starting design/target."""
    clean_name = name.strip()
    clean_objective = objective.strip()
    if not clean_name:
        raise ValueError("Project name is required.")
    if not clean_objective:
        raise ValueError("Scientific objective is required.")

    project_dir = projects_root / make_slug(clean_name)
    if project_dir.exists():
        raise ValueError(f"Project already exists: {project_dir.name}")

    normalized_sequence = normalize_sequence(sequence) if sequence and sequence.strip() else None
    normalized_target = normalize_sequence(target_sequence) if target_sequence and target_sequence.strip() else None

    project = DesignProject(name=clean_name, root_dir=project_dir)
    objective_record = ProjectObjective(description=clean_objective)
    project.archive.add_objective(objective_record)

    if normalized_sequence is not None:
        project.archive.add_design(
            Design(
                name=(design_name or "Starting sequence").strip() or "Starting sequence",
                sequence=normalized_sequence,
                origin="natural_sequence",
                objective_id=objective_record.id,
                hypothesis="Starting sequence registered from the local web workspace.",
            )
        )

    if target_name and target_name.strip():
        project.archive.add_target(
            Target(
                name=target_name.strip(),
                sequence=normalized_target,
                notes="Binder-design target registered from the local web workspace.",
            )
        )

    project.save()
    return project


def create_derived_sequence_design(
    project: DesignProject,
    *,
    parent_design_id: str,
    sequence: str,
    name: str | None = None,
    hypothesis: str | None = None,
) -> Design:
    """Create a child design from an edited sequence without rewriting history."""
    parent = project.archive.get_design(parent_design_id)
    normalized = normalize_sequence(sequence)
    if parent.sequence == normalized:
        raise ValueError("Edited sequence is identical to the selected design.")

    changes: list[dict[str, object]] = []
    if parent.sequence is not None and len(parent.sequence) == len(normalized):
        for position, (old, new) in enumerate(zip(parent.sequence, normalized), start=1):
            if old != new:
                changes.append({"position": position, "from": old, "to": new})

    child = Design(
        name=(name or f"{project.archive.get_design_label(parent.id)} edited").strip(),
        sequence=normalized,
        parent_design_id=parent.id,
        status="active",
        origin="sequence_design",
        objective_id=parent.objective_id,
        target_id=parent.target_id,
        hypothesis=(hypothesis or "").strip() or None,
        metadata={
            "edited_from_design_id": parent.id,
            "sequence_changes": changes,
            "sequence_length_change": len(normalized) - len(parent.sequence or ""),
        },
    )
    project.archive.add_design(child)
    project.archive.add_evidence(
        EvidenceEntry(
            source_type="note",
            source_name="HGD sequence editor",
            summary=f"Created derived sequence design from {project.archive.get_design_label(parent.id)}.",
            design_id=child.id,
            data={"sequence_changes": changes},
        )
    )
    project.save()
    return child


def register_design(
    project: DesignProject,
    *,
    name: str,
    origin: str,
    sequence: str | None = None,
    parent_design_id: str | None = None,
    hypothesis: str | None = None,
    source_tool: str | None = None,
) -> Design:
    """Register an imported/generated design without assuming an evaluator."""
    if origin not in DESIGN_ORIGINS:
        raise ValueError(f"Unsupported design origin: {origin}")
    if parent_design_id is not None:
        project.archive.get_design(parent_design_id)
    normalized = normalize_sequence(sequence) if sequence and sequence.strip() else None
    design = Design(
        name=name.strip() or "Registered design",
        sequence=normalized,
        origin=origin,  # type: ignore[arg-type]
        parent_design_id=parent_design_id,
        objective_id=next(iter(project.archive.objectives), None),
        target_id=next(iter(project.archive.targets), None),
        hypothesis=(hypothesis or "").strip() or None,
    )
    project.archive.add_design(design)
    project.archive.add_evidence(
        EvidenceEntry(
            source_type="computational",
            source_name=(source_tool or "external design workflow").strip() or "external design workflow",
            summary=f"Registered design {design.id}.",
            design_id=design.id,
        )
    )
    project.save()
    return design


def attach_structure_file(
    project: DesignProject,
    *,
    design_id: str,
    source_path: Path,
    source: str,
    method: str | None = None,
    mean_plddt: float | None = None,
    ptm: float | None = None,
    iptm: float | None = None,
    notes: str | None = None,
) -> StructureModel:
    """Copy one structure into the project and register its provenance."""
    project.archive.get_design(design_id)
    if source not in STRUCTURE_SOURCES:
        raise ValueError(f"Unsupported structure source: {source}")
    if source_path.suffix.lower() not in STRUCTURE_SUFFIXES:
        raise ValueError("Structure must be PDB, CIF, or mmCIF.")
    if mean_plddt is not None and not 0 <= mean_plddt <= 100:
        raise ValueError("Mean pLDDT must be between 0 and 100.")
    for label, value in (("pTM", ptm), ("ipTM", iptm)):
        if value is not None and not 0 <= value <= 1:
            raise ValueError(f"{label} must be between 0 and 1.")

    destination = unique_destination(project.structures_dir, source_path.name)
    shutil.copy2(source_path, destination)
    relative_path = str(destination.relative_to(project.root_dir))
    structure = StructureModel(
        design_id=design_id,
        structure_path=relative_path,
        source=source,  # type: ignore[arg-type]
        method=(method or "").strip() or None,
        mean_plddt=mean_plddt,
        ptm=ptm,
        iptm=iptm,
        notes=(notes or "").strip() or None,
    )
    project.archive.add_structure(structure)
    project.archive.add_evidence(
        EvidenceEntry(
            source_type="experimental" if source == "experimental" else "computational",
            source_name=(method or source).strip(),
            summary=f"Attached structure model {structure.id}.",
            design_id=design_id,
            structure_id=structure.id,
            file_paths=[relative_path],
        )
    )
    project.save()
    return structure


def delete_evidence(project: DesignProject, evidence_id: str) -> list[str]:
    """Delete one evidence record and only its private evidence-directory files."""
    try:
        evidence = project.archive.evidence[evidence_id]
    except KeyError as error:
        raise KeyError(f"Unknown evidence: {evidence_id}") from error

    deleted_files: list[str] = []
    evidence_root = project.evidence_dir.resolve()
    for relative in evidence.file_paths:
        candidate = (project.root_dir / relative).resolve()
        try:
            candidate.relative_to(evidence_root)
        except ValueError:
            # Structure files or external references are never deleted with evidence.
            continue
        if candidate.is_file():
            candidate.unlink()
            deleted_files.append(relative)
        parent = candidate.parent
        while parent != evidence_root and parent.exists():
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent

    del project.archive.evidence[evidence_id]
    project.save()
    return deleted_files
