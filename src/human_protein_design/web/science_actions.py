"""Scientific actions exposed by the v0.4 local web workspace.

The CLI scripts and browser UI call the same underlying archive/scoring code. This
module contains the state-changing scientific operations that should not live in
FastAPI route handlers or React components.
"""

from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from human_protein_design.archive import (
    Decision,
    DesignProject,
    EvidenceEntry,
    StructureModel,
    export_obsidian_vault,
    export_project_summary,
)
from human_protein_design.fasta import normalize_sequence, validate_amino_acid


def resolve_design_structure(project: DesignProject, design_id: str) -> Path:
    """Return the newest usable structure for a design."""
    design = project.archive.get_design(design_id)
    structures = project.archive.get_design_structures(design_id)
    stored: str | None = None
    if structures:
        newest = max(structures, key=lambda item: item.created_at)
        stored = newest.structure_path
    elif design.structure_path:
        stored = design.structure_path
    if not stored:
        raise ValueError("This design has no structure. Attach a structure before running PyRosetta.")

    candidate = Path(stored)
    if not candidate.is_absolute():
        candidate = project.root_dir / candidate
    candidate = candidate.resolve()
    if not candidate.is_file():
        raise ValueError(f"Stored structure could not be found: {stored}")
    return candidate


def _pyrosetta_tools():
    """Import PyRosetta-backed modules only when a scientific action is invoked."""
    try:
        import pyrosetta
        from human_protein_design.mutation import get_spatial_neighbors
        from human_protein_design.scan import scan_position
        from human_protein_design.scoring import (
            get_score_terms,
            get_standard_score_function,
            initialize_pyrosetta,
        )
        from human_protein_design.session import DesignSession
    except ImportError as error:
        raise RuntimeError(
            "PyRosetta is not available in this HGD environment. Install/update from environment.yml and restart HGD."
        ) from error
    return (
        pyrosetta,
        get_spatial_neighbors,
        scan_position,
        get_score_terms,
        get_standard_score_function,
        initialize_pyrosetta,
        DesignSession,
    )


def _load_pose(project: DesignProject, design_id: str):
    (
        pyrosetta,
        _get_spatial_neighbors,
        _scan_position,
        _get_score_terms,
        _get_standard_score_function,
        initialize_pyrosetta,
        _DesignSession,
    ) = _pyrosetta_tools()
    initialize_pyrosetta()
    structure_path = resolve_design_structure(project, design_id)
    try:
        pose = pyrosetta.pose_from_file(str(structure_path))
    except Exception as error:  # PyRosetta raises several wrapped C++ exception types.
        raise ValueError(f"PyRosetta could not load {structure_path.name}: {error}") from error
    return pose, structure_path


def _structure_sequence_status(project: DesignProject, design_id: str, pose) -> dict[str, object]:
    """Describe whether a loaded pose can safely represent a design sequence."""
    design = project.archive.get_design(design_id)
    raw_pose_sequence = pose.sequence()
    try:
        pose_sequence = normalize_sequence(raw_pose_sequence)
        canonical_pose = True
    except ValueError:
        pose_sequence = raw_pose_sequence
        canonical_pose = False

    design_sequence = design.sequence
    design_length = len(design_sequence) if design_sequence else None
    pose_length = pose.total_residue()
    exact_match = bool(
        design_sequence
        and canonical_pose
        and len(design_sequence) == pose_length
        and design_sequence == pose_sequence
    )

    warning: str | None = None
    if design_sequence is None:
        if not canonical_pose:
            warning = (
                "The structure contains non-canonical or unsupported residues, so HGD cannot derive a safe "
                "design sequence from it for mutation design."
            )
    elif design_length != pose_length:
        warning = (
            f"Design/structure mismatch: this design has {design_length} residues, but the selected structure "
            f"contains {pose_length}. Attach a structure that represents this design before running mutations or scans."
        )
    elif not canonical_pose:
        warning = (
            "The structure sequence contains non-canonical or unsupported residues. HGD can score the structure, "
            "but cannot safely create mutation children from it."
        )
    elif design_sequence != pose_sequence:
        mismatch_positions = [
            index
            for index, (design_aa, pose_aa) in enumerate(zip(design_sequence, pose_sequence), start=1)
            if design_aa != pose_aa
        ]
        preview = ", ".join(map(str, mismatch_positions[:8]))
        suffix = "…" if len(mismatch_positions) > 8 else ""
        warning = (
            f"Design/structure sequence mismatch at {len(mismatch_positions)} position(s)"
            f" ({preview}{suffix}). Attach the matching structure before mutation design."
        )

    return {
        "design_sequence_length": design_length,
        "structure_sequence_length": pose_length,
        "sequence_match": exact_match if design_sequence else canonical_pose,
        "sequence_warning": warning,
        "pose_sequence": pose_sequence,
    }


def _require_mutation_compatible_structure(project: DesignProject, design_id: str, pose) -> None:
    """Reject mutation/scanning when residue numbering cannot safely map to the design."""
    status = _structure_sequence_status(project, design_id, pose)
    warning = status["sequence_warning"]
    if warning:
        raise ValueError(str(warning))


def score_current_structure(
    project: DesignProject,
    *,
    design_id: str,
) -> EvidenceEntry:
    """Score the current design structure without creating a mutation."""
    (
        _pyrosetta,
        _get_spatial_neighbors,
        _scan_position,
        get_score_terms,
        get_standard_score_function,
        _initialize_pyrosetta,
        _DesignSession,
    ) = _pyrosetta_tools()
    pose, structure_path = _load_pose(project, design_id)
    scores = get_score_terms(pose, get_standard_score_function())
    compatibility = _structure_sequence_status(project, design_id, pose)
    evidence = EvidenceEntry(
        source_type="computational",
        source_name="PyRosetta structure score",
        summary=f"Rosetta full-atom score for {structure_path.name}.",
        design_id=design_id,
        data={
            "analysis_type": "structure_score",
            "structure_file": str(structure_path.name),
            "residue_count": pose.total_residue(),
            "sequence": pose.sequence(),
            "total_score": scores["total_score"],
            "score_terms": scores,
            **compatibility,
        },
    )
    project.archive.add_evidence(evidence)
    project.save()
    return evidence


def run_position_scan(
    project: DesignProject,
    *,
    design_id: str,
    position: int,
    radius: float = 8.0,
) -> tuple[EvidenceEntry, list[dict[str, float | int | str]], list[int], str]:
    """Evaluate all 19 substitutions at one residue and archive the ranking."""
    (
        _pyrosetta,
        get_spatial_neighbors,
        scan_position,
        _get_score_terms,
        get_standard_score_function,
        _initialize_pyrosetta,
        _DesignSession,
    ) = _pyrosetta_tools()
    pose, _ = _load_pose(project, design_id)
    _require_mutation_compatible_structure(project, design_id, pose)
    if position < 1 or position > pose.total_residue():
        raise ValueError(f"Position must be between 1 and {pose.total_residue()}.")
    if radius <= 0:
        raise ValueError("Scan radius must be greater than zero.")

    score_function = get_standard_score_function()
    wt_aa = pose.residue(position).name1()
    results = scan_position(
        pose,
        position=position,
        score_function=score_function,
        radius=radius,
    )
    neighbors = get_spatial_neighbors(
        pose,
        center_position=position,
        radius=radius,
    )

    scan_dir = project.evidence_dir / "mutation_scans"
    scan_dir.mkdir(parents=True, exist_ok=True)
    base = f"{project.archive.get_design_label(design_id)}_{wt_aa}{position}_scan"
    safe = "".join(char if char.isalnum() or char in "-_" else "_" for char in base).strip("_")
    output = scan_dir / f"{safe or f'position_{position}_scan'}.csv"
    counter = 2
    while output.exists():
        output = scan_dir / f"{safe}_{counter}.csv"
        counter += 1

    fieldnames: list[str] = []
    for row in results:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    relative = str(output.relative_to(project.root_dir))
    evidence = EvidenceEntry(
        source_type="computational",
        source_name="PyRosetta saturation scan",
        summary=f"All substitutions scanned at {wt_aa}{position} ({radius:.1f} Å local protocol).",
        design_id=design_id,
        file_paths=[relative],
        data={
            "analysis_type": "position_saturation_scan",
            "position": position,
            "wt_aa": wt_aa,
            "radius_angstrom": radius,
            "neighbors": neighbors,
            "results": results,
            "best_mutation": results[0]["mutation"] if results else None,
            "best_delta_score": results[0]["delta_score"] if results else None,
        },
    )
    project.archive.add_evidence(evidence)
    project.save()
    return evidence, results, neighbors, relative


def evaluate_point_mutation(
    project: DesignProject,
    *,
    design_id: str,
    position: int,
    mutant_aa: str,
    hypothesis: str,
    objective: str,
    design_name: str | None = None,
    radius: float = 8.0,
) -> tuple[str, dict[str, object]]:
    """Evaluate one point mutation and persist it as an undecided child design."""
    (
        _pyrosetta,
        _get_spatial_neighbors,
        _scan_position,
        _get_score_terms,
        get_standard_score_function,
        _initialize_pyrosetta,
        DesignSession,
    ) = _pyrosetta_tools()
    pose, _ = _load_pose(project, design_id)
    _require_mutation_compatible_structure(project, design_id, pose)
    if position < 1 or position > pose.total_residue():
        raise ValueError(f"Position must be between 1 and {pose.total_residue()}.")
    mutant_aa = validate_amino_acid(mutant_aa)
    if radius <= 0:
        raise ValueError("Mutation radius must be greater than zero.")

    session = DesignSession(
        pose=pose,
        score_function=get_standard_score_function(),
        archive=project.archive,
        current_design_id=design_id,
        archive_path=project.archive_path,
        structures_dir=project.structures_dir,
        radius=radius,
    )
    _mutant_pose, result, analysis, context = session.evaluate_mutation(
        position,
        mutant_aa,
        hypothesis=hypothesis.strip(),
        objective=objective.strip(),
        design_name=(design_name or "").strip() or None,
    )
    candidate_id = session.pending_design_id
    if candidate_id is None:
        raise RuntimeError("PyRosetta evaluation did not produce a candidate design.")

    parent = session.archive.get_design(design_id)
    candidate = session.archive.get_design(candidate_id)
    candidate.origin = "point_mutation"
    candidate.objective_id = parent.objective_id
    candidate.target_id = parent.target_id
    candidate.hypothesis = hypothesis.strip() or None

    if candidate.structure_path:
        structure_path = Path(candidate.structure_path).resolve()
        try:
            relative = str(structure_path.relative_to(project.root_dir.resolve()))
        except ValueError:
            relative = str(structure_path)
        candidate.structure_path = relative
        session.archive.add_structure(
            StructureModel(
                design_id=candidate_id,
                structure_path=relative,
                source="rosetta",
                method="PyRosetta local mutation / repack / minimization",
                notes=f"Generated during evaluation of {result.mutation}.",
            )
        )

    project.archive = session.archive
    project.save()
    payload: dict[str, object] = {
        "mutation": result.mutation,
        "position": result.position,
        "wt_aa": result.wt_aa,
        "mutant_aa": result.mutant_aa,
        "previous_score": result.previous_score,
        "mutant_score": result.mutant_score,
        "delta_score": result.delta_score,
        "parent_score_terms": analysis.wt_terms,
        "mutant_score_terms": analysis.mutant_terms,
        "delta_score_terms": analysis.delta_terms,
        "improved_terms": analysis.improved_terms,
        "worsened_terms": analysis.worsened_terms,
        "context": {
            "position": context.position,
            "wt_aa": context.wt_aa,
            "mutant_aa": context.mutant_aa,
            "radius_angstrom": radius,
            "nearby_residues": [asdict(item) for item in context.nearby_residues],
        },
    }
    return candidate_id, payload


def decide_candidate(
    project: DesignProject,
    *,
    candidate_design_id: str,
    outcome: str,
    rationale: str,
    user_note: str | None = None,
) -> Decision:
    """Append a scientist decision; previous decisions remain part of provenance."""
    if outcome not in {"accepted", "rejected", "deferred"}:
        raise ValueError("Decision must be accepted, rejected, or deferred.")
    candidate = project.archive.get_design(candidate_design_id)
    parent_id = candidate.parent_design_id
    if parent_id is None:
        raise ValueError("Root designs cannot be accepted/rejected as mutation candidates.")

    decision = Decision(
        parent_design_id=parent_id,
        candidate_design_id=candidate_design_id,
        outcome=outcome,  # type: ignore[arg-type]
        hypothesis=str(candidate.metadata.get("hypothesis", candidate.hypothesis or "")),
        objective=str(candidate.metadata.get("objective", "")),
        rationale=rationale.strip(),
        user_note=(user_note or "").strip() or None,
    )
    project.archive.add_decision(decision)
    if outcome == "accepted":
        candidate.status = "active"
    elif outcome == "rejected":
        candidate.status = "deprioritized"
    project.save()
    return decision


def export_obsidian(project: DesignProject) -> Path:
    """Export the current archive as an Obsidian-friendly Markdown vault."""
    output = project.root_dir / "obsidian"
    export_obsidian_vault(archive=project.archive, output_dir=output)
    return output


def generate_project_summary(project: DesignProject) -> Path:
    """Generate/update the project-wide Markdown scientific summary."""
    return export_project_summary(
        archive=project.archive,
        output_path=project.root_dir / "PROJECT_SUMMARY.md",
        project_name=project.name,
    )
