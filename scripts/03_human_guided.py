import pyrosetta

from datetime import datetime
from pathlib import Path

from human_protein_design.analysis import MutationAnalysis
from human_protein_design.archive import DesignProject
from human_protein_design.cli import (
    ask_int,
    ask_text,
    ask_yes_no,
    choose_item,
    choose_project,
)
from human_protein_design.context import MutationContext
from human_protein_design.fasta import validate_amino_acid
from human_protein_design.interpretation import interpret_energy_changes
from human_protein_design.scoring import (
    get_standard_score_function,
    initialize_pyrosetta,
)
from human_protein_design.session import DesignSession


def print_result(result, analysis: MutationAnalysis, context: MutationContext) -> None:
    """Print mutation feedback."""
    print("\nMutation result")
    print("-" * 50)
    print(f"Mutation:       {result.mutation}")
    print(f"Previous score: {analysis.wt_total_score:.3f}")
    print(f"Mutant score:   {analysis.mutant_total_score:.3f}")
    print(f"ΔScore:         {analysis.delta_total_score:+.3f} REU")

    print("\nEnergy changes")
    print("-" * 50)
    print(f"{'Term':<20}{'Previous':>10}{'Mutant':>10}{'Δ':>10}")
    print("-" * 50)
    for term, delta in analysis.delta_terms.items():
        if term == "total_score":
            continue
        print(
            f"{term:<20}"
            f"{analysis.wt_terms[term]:>10.3f}"
            f"{analysis.mutant_terms[term]:>10.3f}"
            f"{delta:>+10.3f}"
        )

    if analysis.improved_terms:
        print("\nImproved terms")
        for term in analysis.improved_terms:
            if term != "total_score":
                print(f"  ↓ {term:<18}{analysis.delta_terms[term]:+.3f}")

    if analysis.worsened_terms:
        print("\nWorsened terms")
        for term in analysis.worsened_terms:
            if term != "total_score":
                print(f"  ↑ {term:<18}{analysis.delta_terms[term]:+.3f}")

    if context.nearby_residues:
        print("\nNearby residues")
        print("-" * 50)
        for residue in context.nearby_residues:
            print(f"{residue.amino_acid}{residue.position:<6}{residue.distance:>8.2f} Å")

    interpretations = interpret_energy_changes(analysis)
    if interpretations:
        print("\nInterpretation")
        print("-" * 50)
        for item in interpretations:
            symbol = "↓" if item.direction == "improved" else "↑"
            print(f"{symbol} {item.term:<16}{item.delta:+8.3f}  {item.message}")


def resolve_structure_path(project: DesignProject, structure_path: str) -> Path:
    """Resolve a stored project-relative or absolute structure path."""
    path = Path(structure_path)
    if path.is_absolute() and path.exists():
        return path
    candidate = project.root_dir / path
    if candidate.exists():
        return candidate
    if path.exists():
        return path
    raise FileNotFoundError(f"Could not find stored structure: {structure_path}")


def available_structure_path(project: DesignProject, design) -> str | None:
    """Return the newest first-class structure, falling back to v0.3 structure_path."""
    structures = project.archive.get_design_structures(design.id)
    if structures:
        latest = max(structures, key=lambda structure: structure.created_at)
        return latest.structure_path
    return design.structure_path


def starting_design_label(project: DesignProject, design) -> str:
    latest_decision = project.archive.get_latest_decision(design.id)
    decision = latest_decision.outcome if latest_decision else "none"
    structures = project.archive.get_design_structures(design.id)
    legacy = 1 if design.structure_path and not structures else 0
    return (
        f"{project.archive.get_lineage_label(design.id)} | "
        f"status={design.status} | decision={decision} | "
        f"structures={len(structures) + legacy}"
    )


def choose_starting_design(project: DesignProject):
    """Choose a design that has an available structure."""
    designs = sorted(project.archive.designs.values(), key=lambda design: design.created_at)
    usable = [design for design in designs if available_structure_path(project, design)]
    if not usable:
        return None
    return choose_item(
        usable,
        "Continue from design",
        label=lambda item: starting_design_label(project, item),
    )


def ask_mutant_aa(position: int, current_aa: str) -> str:
    """Ask until a valid single-letter mutation is entered."""
    while True:
        raw = ask_text("Mutate to")
        try:
            mutant_aa = validate_amino_acid(raw)
        except ValueError as error:
            print(error)
            continue
        if mutant_aa == current_aa:
            print(f"Residue {position} is already {current_aa}. Choose a different amino acid.")
            continue
        return mutant_aa


def main() -> None:
    """Run the PyRosetta human-guided point-mutation workflow."""
    initialize_pyrosetta()
    score_function = get_standard_score_function()

    project_dir = choose_project()
    project = DesignProject.load(name=project_dir.name, root_dir=project_dir)

    if not project.archive.designs:
        raise SystemExit(
            "This project contains no designs. Create/register a design and attach a structure before running PyRosetta mutation design."
        )

    current_design = choose_starting_design(project)
    if current_design is None:
        raise SystemExit(
            "No design in this project has an attached structure. Use scripts/10_add_structure.py first."
        )

    stored_structure = available_structure_path(project, current_design)
    assert stored_structure is not None
    structure_path = resolve_structure_path(project, stored_structure)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = project.sessions_dir / f"session_{timestamp}"
    session_dir.mkdir(parents=True, exist_ok=True)

    pose = pyrosetta.pose_from_pdb(str(structure_path))
    session = DesignSession(
        pose=pose,
        score_function=score_function,
        archive=project.archive,
        current_design_id=current_design.id,
        archive_path=project.archive_path,
        structures_dir=project.structures_dir,
        output_dir=session_dir,
    )

    print("\nContinuing existing project.")
    print("Starting lineage:")
    print("  " + project.archive.get_lineage_label(current_design.id))

    print("\nHuman-Guided Protein Design")
    print("=" * 50)

    while True:
        print(f"\nCurrent sequence:\n{session.pose.sequence()}")
        position = ask_int(
            "Position (or 'q' to quit)",
            minimum=1,
            maximum=session.pose.total_residue(),
            allow_quit=True,
        )
        if position is None:
            break

        current_aa = session.pose.residue(position).name1()
        print(f"Current residue: {current_aa}{position}")
        mutant_aa = ask_mutant_aa(position, current_aa)

        design_name = ask_text("Design name (optional; automatic if blank)", required=False) or None
        hypothesis = ask_text("Hypothesis (what do you expect this mutation to do?)")
        objective = ask_text("Objective (what are you trying to improve/test?)")

        try:
            mutant_pose, result, analysis, context = session.evaluate_mutation(
                position,
                mutant_aa,
                hypothesis=hypothesis,
                objective=objective,
                design_name=design_name,
            )
        except (ValueError, RuntimeError) as error:
            print(error)
            continue

        print_result(result, analysis, context)
        accepted = ask_yes_no("Accept mutation?", default=False)
        rationale = ask_text("Rationale (why are you making this decision?)")

        if accepted:
            session.accept_mutation(mutant_pose, result, rationale=rationale)
            print(f"\nAccepted {result.mutation}")
            if session.current_design_id is not None:
                print("Lineage: " + session.archive.get_lineage_label(session.current_design_id))
        else:
            session.reject_mutation(rationale=rationale)
            print(f"\nRejected {result.mutation}")
            print("Candidate retained in design archive.")

    print("\nDesign session finished.")
    if session.history:
        print("\nAccepted mutations this session:")
        for result in session.history:
            print(f"  {result.mutation:<8}ΔScore {result.delta_score:+.3f}")
    else:
        print("\nNo mutations were accepted during this session.")

    csv_path = session_dir / "history.csv"
    json_path = session_dir / "history.json"
    pdb_path = session_dir / "final_design.pdb"
    session.save_history_csv(csv_path)
    session.save_history_json(json_path)
    session.pose.dump_pdb(str(pdb_path))

    project.archive = session.archive
    project.save()

    print(f"\nSession saved to:\n{session_dir}")
    print(f"\nProject archive:\n{project.archive_path}")
    if session.current_design_id is not None:
        print("\nCurrent design lineage:")
        print("  " + session.archive.get_lineage_label(session.current_design_id))


if __name__ == "__main__":
    main()
