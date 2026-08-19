"""Protein mutation utilities using PyRosetta."""

import pyrosetta

from pyrosetta.rosetta.core.pose import Pose
from pyrosetta.rosetta.core.kinematics import MoveMap
from pyrosetta.rosetta.protocols.minimization_packing import (
    MinMover,
    PackRotamersMover,
)

from human_protein_design.fasta import validate_amino_acid


AA_1_TO_3 = {
    "A": "ALA",
    "C": "CYS",
    "D": "ASP",
    "E": "GLU",
    "F": "PHE",
    "G": "GLY",
    "H": "HIS",
    "I": "ILE",
    "K": "LYS",
    "L": "LEU",
    "M": "MET",
    "N": "ASN",
    "P": "PRO",
    "Q": "GLN",
    "R": "ARG",
    "S": "SER",
    "T": "THR",
    "V": "VAL",
    "W": "TRP",
    "Y": "TYR",
}


def mutate_pose(
    pose: Pose,
    position: int,
    mutant_aa: str,
) -> Pose:
    """Return a copy of pose with one residue mutated."""

    mutant_aa = validate_amino_acid(mutant_aa)

    if not 1 <= position <= pose.total_residue():
        raise ValueError(
            f"Position {position} is outside the pose "
            f"(1-{pose.total_residue()})."
        )

    mutant_pose = Pose()
    mutant_pose.assign(pose)

    chemical_manager = (
        pyrosetta.rosetta.core.chemical
        .ChemicalManager.get_instance()
    )

    residue_type_set = (
        chemical_manager.residue_type_set(
            "fa_standard"
        )
    )

    mutant_type = residue_type_set.name_map(
        AA_1_TO_3[mutant_aa]
    )

    mutant_residue = (
        pyrosetta.rosetta.core.conformation
        .ResidueFactory.create_residue(
            mutant_type
        )
    )

    mutant_pose.replace_residue(
        position,
        mutant_residue,
        True,
    )

    return mutant_pose


def get_spatial_neighbors(
    pose: Pose,
    center_position: int,
    radius: float = 8.0,
) -> list[int]:
    """Return residues whose neighbor atoms are within radius of center."""

    center_xyz = (
        pose.residue(center_position)
        .nbr_atom_xyz()
    )

    radius_squared = radius ** 2

    neighbors = []

    for position in range(
        1,
        pose.total_residue() + 1,
    ):
        residue_xyz = (
            pose.residue(position)
            .nbr_atom_xyz()
        )

        distance_squared = (
            center_xyz.distance_squared(
                residue_xyz
            )
        )

        if distance_squared <= radius_squared:
            neighbors.append(position)

    return neighbors


def repack_local_pose(
    pose: Pose,
    score_function,
    center_position: int,
    radius: float = 8.0,
) -> Pose:
    """Repack side chains within a spatial neighborhood."""

    repacked_pose = Pose()
    repacked_pose.assign(pose)

    neighbors = get_spatial_neighbors(
        repacked_pose,
        center_position=center_position,
        radius=radius,
    )

    task = pyrosetta.standard_packer_task(
        repacked_pose
    )

    # Never allow sequence design.
    task.restrict_to_repacking()

    # Freeze everything outside the neighborhood.
    for position in range(
        1,
        repacked_pose.total_residue() + 1,
    ):
        if position not in neighbors:
            task.nonconst_residue_task(
                position
            ).prevent_repacking()

    packer = PackRotamersMover(
        score_function,
        task,
    )

    packer.apply(repacked_pose)

    return repacked_pose


def minimize_local_pose(
    pose: Pose,
    score_function,
    center_position: int,
    radius: float = 8.0,
    backbone_window: int = 1,
) -> Pose:
    """
    Locally minimize a pose.

    Side chains:
        movable for residues within `radius` Å of the mutation.

    Backbone:
        movable only for the mutation site and nearby sequence residues
        defined by `backbone_window`.
    """

    minimized_pose = Pose()
    minimized_pose.assign(pose)

    # Spatial neighborhood for side-chain relaxation
    neighbors = get_spatial_neighbors(
        minimized_pose,
        center_position=center_position,
        radius=radius,
    )

    movemap = MoveMap()

    # Explicitly freeze everything first
    movemap.set_bb(False)
    movemap.set_chi(False)
    movemap.set_jump(False)

    # --------------------------------
    # Side chains: spatial neighborhood
    # --------------------------------

    for position in neighbors:
        movemap.set_chi(
            position,
            True,
        )

    # --------------------------------
    # Backbone: very small sequence window
    # --------------------------------

    bb_start = max(
        1,
        center_position - backbone_window,
    )

    bb_end = min(
        minimized_pose.total_residue(),
        center_position + backbone_window,
    )

    for position in range(
        bb_start,
        bb_end + 1,
    ):
        movemap.set_bb(
            position,
            True,
        )

    # --------------------------------
    # Minimization
    # --------------------------------

    minimizer = MinMover()

    minimizer.movemap(
        movemap
    )

    minimizer.score_function(
        score_function
    )

    minimizer.min_type(
        "lbfgs_armijo_nonmonotone"
    )

    minimizer.tolerance(
        0.01
    )

    minimizer.apply(
        minimized_pose
    )
    return minimized_pose
