#!/usr/bin/env python3
"""Create a structure-independent Human-Guided Protein Design project."""

from __future__ import annotations

import shutil
from pathlib import Path

from human_protein_design.archive import (
    Design,
    DesignProject,
    ProjectObjective,
    StructureModel,
    Target,
)
from human_protein_design.cli import (
    ask_choice,
    ask_text,
    choose_file,
)
from human_protein_design.fasta import normalize_sequence, read_single_fasta


PROJECTS_ROOT = Path("data/projects")
STRUCTURE_SUFFIXES = {".pdb", ".cif", ".mmcif"}
FASTA_SUFFIXES = {".fasta", ".fa", ".faa", ".fas"}


def make_slug(name: str) -> str:
    """Return a filesystem-safe project slug."""
    slug = "".join(
        char for char in "_".join(name.lower().split())
        if char.isalnum() or char in {"_", "-"}
    ).strip("_-")
    if not slug:
        raise ValueError("Project name does not produce a valid directory name.")
    return slug


def ask_new_project_name() -> tuple[str, Path]:
    """Ask until an unused project name is supplied."""
    while True:
        name = ask_text("Project name")
        try:
            project_dir = PROJECTS_ROOT / make_slug(name)
        except ValueError as error:
            print(error)
            continue
        if project_dir.exists():
            print(f"Project directory already exists: {project_dir}")
            continue
        return name, project_dir


def ask_sequence(prompt: str, *, required: bool = False) -> str | None:
    """Ask until a valid protein sequence is supplied or skipped."""
    while True:
        raw = ask_text(prompt, required=required)
        if not raw and not required:
            return None
        try:
            return normalize_sequence(raw)
        except ValueError as error:
            print(error)


def copy_into(source: Path, destination_dir: Path) -> str:
    """Copy a validated input file and return a project-relative path."""
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / source.name
    if destination.exists():
        stem, suffix, counter = destination.stem, destination.suffix, 2
        while destination.exists():
            destination = destination_dir / f"{stem}_{counter}{suffix}"
            counter += 1
    shutil.copy2(source, destination)
    return str(destination.relative_to(destination_dir.parent))


def main() -> None:
    """Collect and validate all inputs, then create the project atomically enough for CLI use."""
    print("\nHuman-Guided Protein Design — v0.3.5")
    print("Create a new research project\n")

    # Phase 1: collect and validate everything. Nothing is written yet.
    project_name, project_dir = ask_new_project_name()
    objective_text = ask_text("Scientific objective")

    print(
        "\nStarting material:\n"
        "  1. Experimental structure\n"
        "  2. Predicted structure\n"
        "  3. Protein sequence only\n"
        "  4. De novo design objective\n"
        "  5. Protein target / binder design"
    )
    mode = ask_choice(
        "Choose",
        {"1": "experimental", "2": "predicted", "3": "sequence", "4": "de_novo", "5": "binder"},
    )

    structure_file: Path | None = None
    structure_source: str | None = None
    method: str | None = None
    sequence: str | None = None
    sequence_name = "Starting sequence"
    length = ""
    motif = ""
    target_name = ""
    target_sequence: str | None = None
    target_structure_file: Path | None = None

    if mode in {"experimental", "predicted"}:
        structure_file = choose_file(
            Path.cwd(),
            "Select structure file",
            allowed_suffixes=STRUCTURE_SUFFIXES,
            recursive=True,
        )
        sequence = ask_sequence("Sequence (optional)")
        if mode == "experimental":
            structure_source = "experimental"
            method = ask_text("Experimental method", required=False) or None
        else:
            print("\nPrediction source:\n  1. AlphaFold\n  2. ColabFold\n  3. Other")
            structure_source = ask_choice(
                "Choose source",
                {"1": "alphafold", "2": "colabfold", "3": "other"},
            )
            method = ask_text("Prediction model/method", required=False) or None

    elif mode == "sequence":
        print("\nSequence input:\n  1. FASTA file\n  2. Paste sequence")
        sequence_mode = ask_choice("Choose", {"1": "fasta", "2": "manual"})
        if sequence_mode == "fasta":
            while True:
                fasta_file = choose_file(
                    Path.cwd(),
                    "Select FASTA file",
                    allowed_suffixes=FASTA_SUFFIXES,
                    recursive=True,
                )
                assert fasta_file is not None
                try:
                    sequence_name, sequence = read_single_fasta(fasta_file)
                    sequence = normalize_sequence(sequence)
                    break
                except ValueError as error:
                    print(f"Invalid FASTA: {error}")
        else:
            sequence = ask_sequence("Protein sequence", required=True)
            sequence_name = ask_text("Sequence/design name", required=False, default="Starting sequence")

    elif mode == "de_novo":
        length = ask_text("Length / size constraint", required=False)
        motif = ask_text("Motif / functional constraint", required=False)

    elif mode == "binder":
        target_name = ask_text("Target name")
        target_sequence = ask_sequence("Target sequence (optional)")
        target_structure_file = choose_file(
            Path.cwd(),
            "Select target structure file",
            allowed_suffixes=STRUCTURE_SUFFIXES,
            recursive=True,
            required=False,
        )

    # Phase 2: all required input is valid. Filesystem/archive writes start here.
    project = DesignProject(name=project_name, root_dir=project_dir)
    objective = ProjectObjective(description=objective_text)
    if length:
        objective.constraints.append(f"Length: {length}")
    if motif:
        objective.constraints.append(f"Motif/function: {motif}")
    project.archive.add_objective(objective)

    if mode in {"experimental", "predicted"}:
        assert structure_file is not None and structure_source is not None
        design = Design(
            name="Starting design",
            sequence=sequence,
            origin="imported_design",
            objective_id=objective.id,
        )
        project.archive.add_design(design)
        stored_path = copy_into(structure_file, project.structures_dir)
        project.archive.add_structure(
            StructureModel(
                design_id=design.id,
                structure_path=stored_path,
                source=structure_source,
                method=method,
            )
        )

    elif mode == "sequence":
        assert sequence is not None
        project.archive.add_design(
            Design(
                name=sequence_name,
                sequence=sequence,
                origin="natural_sequence",
                objective_id=objective.id,
                hypothesis="Initial sequence-only design; structure not yet established.",
            )
        )

    elif mode == "binder":
        stored_target_structure = None
        if target_structure_file is not None:
            stored_target_structure = copy_into(target_structure_file, project.structures_dir)
        project.archive.add_target(
            Target(
                name=target_name,
                sequence=target_sequence,
                structure_path=stored_target_structure,
                notes="Binder-design target.",
            )
        )

    project.archive.validate()
    project.save()

    print(f"\nCreated: {project_dir}")
    print(f"Archive schema: {project.archive.SCHEMA_VERSION}")
    print(f"Designs: {len(project.archive.designs)}")
    print(f"Structures: {len(project.archive.structures)}")
    print(f"Targets: {len(project.archive.targets)}")


if __name__ == "__main__":
    main()
