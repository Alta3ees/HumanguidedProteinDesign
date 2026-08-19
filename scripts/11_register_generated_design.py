#!/usr/bin/env python3
"""Register a generated or imported design without assuming PyRosetta."""

from __future__ import annotations

import shutil
from pathlib import Path

from human_protein_design.archive import Design, DesignProject, EvidenceEntry, StructureModel
from human_protein_design.cli import (
    ask_choice,
    ask_text,
    choose_file,
    choose_item,
    choose_project,
)
from human_protein_design.fasta import normalize_sequence


STRUCTURE_SUFFIXES = {".pdb", ".cif", ".mmcif"}


def ask_sequence_optional() -> str | None:
    while True:
        raw = ask_text("Sequence", required=False)
        if not raw:
            return None
        try:
            return normalize_sequence(raw)
        except ValueError as error:
            print(error)


def unique_destination(source: Path, destination_dir: Path) -> Path:
    destination = destination_dir / source.name
    if not destination.exists() or source.resolve() == destination.resolve():
        return destination
    stem, suffix, counter = destination.stem, destination.suffix, 2
    while destination.exists():
        destination = destination_dir / f"{stem}_{counter}{suffix}"
        counter += 1
    return destination


def main() -> None:
    print("\nHuman-Guided Protein Design — v0.3.5")
    print("Register generated/imported design\n")

    project_dir = choose_project()
    project = DesignProject.load(name=project_dir.name, root_dir=project_dir)

    designs = list(project.archive.designs.values())
    parent = choose_item(
        designs,
        "Choose parent",
        label=lambda item: project.archive.get_design_label(item.id),
        allow_none=True,
        none_label="No parent",
    ) if designs else None

    print(
        "\nDesign origin:\n"
        "  1. De novo\n"
        "  2. Generated backbone\n"
        "  3. Sequence design\n"
        "  4. Point mutation\n"
        "  5. Imported design"
    )
    origin = ask_choice(
        "Choose origin",
        {
            "1": "de_novo",
            "2": "generated_backbone",
            "3": "sequence_design",
            "4": "point_mutation",
            "5": "imported_design",
        },
    )

    name = ask_text("Design name")
    sequence = ask_sequence_optional()
    hypothesis = ask_text("Pre-evaluation hypothesis", required=False) or None
    tool = ask_text("Generator / source tool", required=False)
    structure_file = choose_file(
        Path.cwd(),
        "Select structure / backbone file",
        allowed_suffixes=STRUCTURE_SUFFIXES,
        recursive=True,
        required=False,
    )

    objective_id = next(iter(project.archive.objectives), None)
    target_id = next(iter(project.archive.targets), None)
    design = Design(
        name=name,
        sequence=sequence,
        origin=origin,
        parent_design_id=parent.id if parent else None,
        objective_id=objective_id,
        target_id=target_id,
        hypothesis=hypothesis,
    )
    project.archive.add_design(design)

    structure = None
    if structure_file is not None:
        destination = unique_destination(structure_file, project.structures_dir)
        if structure_file.resolve() != destination.resolve():
            shutil.copy2(structure_file, destination)
        source = "rfdiffusion" if tool.lower().startswith("rfdiffusion") else "other"
        structure = StructureModel(
            design_id=design.id,
            structure_path=str(destination.relative_to(project.root_dir)),
            source=source,
            method=tool or None,
        )
        project.archive.add_structure(structure)

    project.archive.add_evidence(
        EvidenceEntry(
            source_type="computational",
            source_name=tool or "external design workflow",
            summary=f"Registered generated/imported design {design.id}.",
            design_id=design.id,
            structure_id=structure.id if structure else None,
        )
    )
    project.archive.validate()
    project.save()

    print(f"\nRegistered {design.name} [{design.id}]")
    print("No Rosetta score or decision was assumed.")


if __name__ == "__main__":
    main()
