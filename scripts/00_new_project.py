#!/usr/bin/env python3
"""Create a structure-independent Human-Guided Protein Design project."""

from __future__ import annotations

import shutil
from pathlib import Path

from human_protein_design.archive import Design, DesignProject, ProjectObjective, StructureModel, Target
from human_protein_design.fasta import normalize_sequence, read_single_fasta

PROJECTS_ROOT = Path("data/projects")


def ask(prompt: str, *, required: bool = True) -> str:
    while True:
        value = input(prompt).strip()
        if value or not required:
            return value


def copy_into(source: Path, destination_dir: Path) -> str:
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / source.name
    shutil.copy2(source, destination)
    return str(destination.relative_to(destination_dir.parent))


def main() -> None:
    print("\nHuman-Guided Protein Design — v0.3.5")
    print("Create a new research project\n")
    project_name = ask("Project name: ")
    slug = "_".join(project_name.lower().split())
    project_dir = PROJECTS_ROOT / slug
    if (project_dir / "design_archive.json").exists():
        raise SystemExit(f"Project already exists: {project_dir}")

    objective_text = ask("Scientific objective: ")
    project = DesignProject(name=project_name, root_dir=project_dir)
    objective = ProjectObjective(description=objective_text)
    project.archive.add_objective(objective)

    print("\nStarting material:\n  1. Experimental structure\n  2. Predicted structure\n  3. Protein sequence only\n  4. De novo design objective\n  5. Protein target / binder design\n")
    mode = ask("Choose [1-5]: ")
    if mode not in {"1", "2", "3", "4", "5"}:
        raise SystemExit("Invalid choice.")

    if mode in {"1", "2"}:
        structure_file = Path(ask("Structure file (.pdb/.cif): ")).expanduser()
        if not structure_file.is_file():
            raise SystemExit(f"File not found: {structure_file}")
        sequence_raw = ask("Sequence [optional]: ", required=False)
        sequence = normalize_sequence(sequence_raw) if sequence_raw else None
        design = Design(name="Starting design", sequence=sequence, origin="imported_design", objective_id=objective.id)
        project.archive.add_design(design)
        stored_path = copy_into(structure_file, project.structures_dir)
        if mode == "1":
            source = "experimental"
            method = ask("Experimental method [optional]: ", required=False) or None
        else:
            source_raw = ask("Prediction source [alphafold/colabfold/other]: ").lower()
            source = source_raw if source_raw in {"alphafold", "colabfold"} else "other"
            method = ask("Prediction model/method [optional]: ", required=False) or None
        project.archive.add_structure(StructureModel(design_id=design.id, structure_path=stored_path, source=source, method=method))

    elif mode == "3":
        fasta_raw = ask("FASTA file [Enter to paste sequence]: ", required=False)
        if fasta_raw:
            name, sequence = read_single_fasta(Path(fasta_raw).expanduser())
        else:
            name = "Starting sequence"
            sequence = normalize_sequence(ask("Protein sequence: "))
        project.archive.add_design(Design(name=name, sequence=sequence, origin="natural_sequence", objective_id=objective.id, hypothesis="Initial sequence-only design; structure not yet established."))

    elif mode == "4":
        length = ask("Length / size constraint [optional]: ", required=False)
        motif = ask("Motif / functional constraint [optional]: ", required=False)
        if length:
            objective.constraints.append(f"Length: {length}")
        if motif:
            objective.constraints.append(f"Motif/function: {motif}")

    elif mode == "5":
        target_name = ask("Target name: ")
        target_sequence_raw = ask("Target sequence [optional]: ", required=False)
        target_sequence = normalize_sequence(target_sequence_raw) if target_sequence_raw else None
        target_structure_raw = ask("Target structure file [optional]: ", required=False)
        target_structure = None
        if target_structure_raw:
            source = Path(target_structure_raw).expanduser()
            if not source.is_file():
                raise SystemExit(f"File not found: {source}")
            target_structure = copy_into(source, project.structures_dir)
        project.archive.add_target(Target(name=target_name, sequence=target_sequence, structure_path=target_structure, notes="Binder-design target."))

    project.save()
    print(f"\nCreated: {project_dir}")
    print(f"Archive schema: {project.archive.SCHEMA_VERSION}")
    print(f"Designs: {len(project.archive.designs)}")
    print(f"Structures: {len(project.archive.structures)}")
    print(f"Targets: {len(project.archive.targets)}")


if __name__ == "__main__":
    main()
