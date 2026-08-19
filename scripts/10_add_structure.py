#!/usr/bin/env python3
"""Attach a structural hypothesis to an existing design."""

from __future__ import annotations

import shutil
from pathlib import Path

from human_protein_design.archive import DesignProject, EvidenceEntry, StructureModel
from human_protein_design.cli import (
    ask_choice,
    ask_float,
    ask_text,
    choose_file,
    choose_item,
    choose_project,
)


STRUCTURE_SUFFIXES = {".pdb", ".cif", ".mmcif"}


def design_label(project: DesignProject, design) -> str:
    structures = project.archive.get_design_structures(design.id)
    sequence_state = "sequence" if design.sequence else "no sequence"
    return (
        f"{project.archive.get_design_label(design.id)} [{design.id[:12]}] "
        f"({sequence_state}, {len(structures)} structure(s))"
    )


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
    print("Attach structure\n")

    project_dir = choose_project()
    project = DesignProject.load(name=project_dir.name, root_dir=project_dir)
    designs = list(project.archive.designs.values())
    if not designs:
        raise SystemExit("Project contains no designs. Register a design first.")

    design = choose_item(
        designs,
        "Choose design",
        label=lambda item: design_label(project, item),
    )
    assert design is not None

    source_file = choose_file(
        Path.cwd(),
        "Select structure file",
        allowed_suffixes=STRUCTURE_SUFFIXES,
        recursive=True,
    )
    assert source_file is not None

    print(
        "\nStructure source:\n"
        "  1. Experimental\n"
        "  2. AlphaFold\n"
        "  3. ColabFold\n"
        "  4. RFdiffusion\n"
        "  5. Rosetta\n"
        "  6. User\n"
        "  7. Other"
    )
    source = ask_choice(
        "Choose source",
        {
            "1": "experimental",
            "2": "alphafold",
            "3": "colabfold",
            "4": "rfdiffusion",
            "5": "rosetta",
            "6": "user",
            "7": "other",
        },
    )

    method = ask_text("Method / model", required=False) or None
    mean_plddt = ask_float("Mean pLDDT (optional)", minimum=0.0, maximum=100.0)
    ptm = ask_float("pTM (optional)", minimum=0.0, maximum=1.0)
    iptm = ask_float("ipTM (optional)", minimum=0.0, maximum=1.0)
    notes = ask_text("Notes", required=False) or None

    destination = unique_destination(source_file, project.structures_dir)
    if source_file.resolve() != destination.resolve():
        shutil.copy2(source_file, destination)
    relative_path = str(destination.relative_to(project.root_dir))

    structure = StructureModel(
        design_id=design.id,
        structure_path=relative_path,
        source=source,
        method=method,
        mean_plddt=mean_plddt,
        ptm=ptm,
        iptm=iptm,
        notes=notes,
    )
    project.archive.add_structure(structure)
    project.archive.add_evidence(
        EvidenceEntry(
            source_type="experimental" if source == "experimental" else "computational",
            source_name=method or source,
            summary=f"Attached structure model {structure.id}.",
            design_id=design.id,
            structure_id=structure.id,
            file_paths=[relative_path],
        )
    )
    project.archive.validate()
    project.save()

    print(f"\nAdded structure {structure.id}")
    print(f"Design: {project.archive.get_design_label(design.id)}")
    print(f"Source: {source}")
    print(f"File: {relative_path}")


if __name__ == "__main__":
    main()
