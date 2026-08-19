#!/usr/bin/env python3
"""Attach a structural hypothesis to an existing design."""

from __future__ import annotations

import shutil
from pathlib import Path

from human_protein_design.archive import DesignProject, EvidenceEntry, StructureModel

ALLOWED_SOURCES = {"experimental", "alphafold", "colabfold", "rfdiffusion", "rosetta", "user", "other"}


def choose_design(project: DesignProject):
    designs = list(project.archive.designs.values())
    if not designs:
        raise SystemExit("Project contains no designs.")
    print("\nDesigns:")
    for index, design in enumerate(designs, start=1):
        structures = project.archive.get_design_structures(design.id)
        sequence_state = "sequence" if design.sequence else "no sequence"
        print(f"  {index}. {project.archive.get_design_label(design.id)} [{design.id[:12]}] ({sequence_state}, {len(structures)} structure(s))")
    raw = input("Choose design number: ").strip()
    try:
        return designs[int(raw) - 1]
    except (ValueError, IndexError):
        raise SystemExit("Invalid design selection.")


def optional_float(prompt: str) -> float | None:
    raw = input(prompt).strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        raise SystemExit(f"Expected a number, got {raw!r}.")


def main() -> None:
    project_dir = Path(input("Project directory: ").strip()).expanduser()
    project = DesignProject.load(name=project_dir.name, root_dir=project_dir)
    design = choose_design(project)
    source_file = Path(input("Structure file: ").strip()).expanduser()
    if not source_file.is_file():
        raise SystemExit(f"File not found: {source_file}")
    source = input("Source [experimental/alphafold/colabfold/rfdiffusion/rosetta/user/other]: ").strip().lower()
    if source not in ALLOWED_SOURCES:
        raise SystemExit("Invalid structure source.")
    destination = project.structures_dir / source_file.name
    if source_file.resolve() != destination.resolve():
        shutil.copy2(source_file, destination)
    relative_path = str(destination.relative_to(project.root_dir))
    structure = StructureModel(
        design_id=design.id,
        structure_path=relative_path,
        source=source,
        method=input("Method / model [optional]: ").strip() or None,
        mean_plddt=optional_float("Mean pLDDT [optional]: "),
        ptm=optional_float("pTM [optional]: "),
        iptm=optional_float("ipTM [optional]: "),
        notes=input("Notes [optional]: ").strip() or None,
    )
    project.archive.add_structure(structure)
    project.archive.add_evidence(EvidenceEntry(
        source_type="experimental" if source == "experimental" else "computational",
        source_name=structure.method or source,
        summary=f"Attached structure model {structure.id}.",
        design_id=design.id,
        structure_id=structure.id,
        file_paths=[relative_path],
    ))
    project.save()
    print(f"\nAdded structure {structure.id}")
    print(f"Design: {project.archive.get_design_label(design.id)}")
    print(f"Source: {source}")
    print(f"File: {relative_path}")


if __name__ == "__main__":
    main()
