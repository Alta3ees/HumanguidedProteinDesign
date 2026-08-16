from dataclasses import dataclass

from pyrosetta.rosetta.core.pose import Pose


@dataclass
class NearbyResidue:
    """Residue near the mutation site."""

    position: int
    amino_acid: str
    distance: float


@dataclass
class MutationContext:
    """Structural context around a proposed mutation."""

    position: int
    wt_aa: str
    mutant_aa: str
    nearby_residues: list[NearbyResidue]


def get_mutation_context(
    pose: Pose,
    position: int,
    mutant_aa: str,
    radius: float = 8.0,
) -> MutationContext:
    """Return residues within a radius of the mutation site."""

    if not 1 <= position <= pose.total_residue():
        raise ValueError(
            f"Position {position} is outside the protein."
        )

    wt_aa = pose.residue(position).name1()
    mutant_aa = mutant_aa.upper()

    center_residue = pose.residue(position)
    center_xyz = center_residue.nbr_atom_xyz()

    nearby_residues = []

    for residue_index in range(
        1,
        pose.total_residue() + 1,
    ):
        if residue_index == position:
            continue

        residue = pose.residue(residue_index)

        distance = (
            center_xyz
            - residue.nbr_atom_xyz()
        ).norm()

        if distance <= radius:
            nearby_residues.append(
                NearbyResidue(
                    position=residue_index,
                    amino_acid=residue.name1(),
                    distance=float(distance),
                )
            )

    nearby_residues.sort(
        key=lambda residue: residue.distance
    )

    return MutationContext(
        position=position,
        wt_aa=wt_aa,
        mutant_aa=mutant_aa,
        nearby_residues=nearby_residues,
    )