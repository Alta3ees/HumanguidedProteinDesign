#!/usr/bin/env python3
"""Register a generated or imported design without assuming PyRosetta."""

from __future__ import annotations

import shutil
from pathlib import Path

from human_protein_design.archive import Design, DesignProject, EvidenceEntry, StructureModel
from human_protein_design.fasta import normalize_sequence

ALLOWED_ORIGINS = {"de_novo", "generated_backbone", "sequence_design", "point_mutation", "imported_design"}


def choose_optional_parent(project: DesignProject):
    designs = list(project.archive.designs.values())
    if not designs:
        return None
    print("\nPossible parents:")
    print("  0. No parent")
    for index, design in enumerate(designs, start=1):
        print(f"  {index}. {project.archive.get_design_label(design.id)}")
    raw = input("Parent [0]: ").strip() or "0"
    try:
        index = int(raw)
    except ValueError:
        raise SystemExit("Invalid parent selection.")
    if index == 0:
        return None
    try:
        return designs[index - 1]
    except IndexError:
        raise SystemExit("Invalid parent selection.")


def main() -> None:
    project_dir = Path(input("Project directory: ").strip()).expanduser()
    project = DesignProject.load(name=project_dir.name, root_dir=project_dir)
    parent = choose_optional_parent(project)
    origin = input("Origin [de_novo/generated_backbone/sequence_design/point_mutation/imported_design]: ").strip()
    if origin not in ALLOWED_ORIGINS:
        raise SystemExit("Invalid origin.")
    name = input("Design name: ").strip()
    sequence_raw = input("Sequence [optional]: ").strip()
    sequence = normalize_sequence(sequence_raw) if sequence_raw else None
    hypothesis = input("Pre-evaluation hypothesis [optional]: ").strip() or None
    objective_id = next(iter(project.archive.objectives), None)
    target_id = next(iter(project.archive.targets), None)
    design = Design(name=name, sequence=sequence, origin=origin, parent_design_id=parent.id if parent else None, objective_id=objective_id, target_id=target_id, hypothesis=hypothesis)
    project.archive.add_design(design)
    tool = input("Generator / source tool [optional]: ").strip()
    structure_raw = input("Structure / backbone file [optional]: ").strip()
    structure = None
    if structure_raw:
        source_file = Path(structure_raw).expanduser()
        if not source_file.is_file():
            raise SystemExit(f"File not found: {source_file}")
        destination = project.structures_dir / source_file.name
        if source_file.resolve() != destination.resolve():
            shutil.copy2(source_file, destination)
        source = "rfdiffusion" if tool.lower().startswith("rfdiffusion") else "other"
        structure = StructureModel(design_id=design.id, structure_path=str(destination.relative_to(project.root_dir)), source=source, method=tool or None)
        project.archive.add_structure(structure)
    project.archive.add_evidence(EvidenceEntry(
        source_type="computational",
        source_name=tool or "external design workflow",
        summary=f"Registered generated/imported design {design.id}.",
        design_id=design.id,
        structure_id=structure.id if structure else None,
    ))
    project.save()
    print(f"\nRegistered {design.name} [{design.id}]")
    print("No Rosetta score or decision was assumed.")


if __name__ == "__main__":
    main()
