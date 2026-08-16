import pyrosetta
import pytest

from human_protein_design.context import (
    get_mutation_context,
)


@pytest.fixture(scope="module", autouse=True)
def initialize_pyrosetta():
    pyrosetta.init(
        "-mute all "
        "-run:constant_seed "
        "-run:jran 1111111"
    )


@pytest.fixture
def test_pose():
    return pyrosetta.pose_from_sequence(
        "ACDEFGHIK"
    )


def test_context_identifies_mutation():

    pose = pyrosetta.pose_from_sequence(
        "ACDEFGHIK"
    )

    context = get_mutation_context(
        pose,
        position=3,
        mutant_aa="W",
        radius=8.0,
    )

    assert context.position == 3
    assert context.wt_aa == "D"
    assert context.mutant_aa == "W"


def test_context_excludes_mutation_site(
    test_pose,
):

    context = get_mutation_context(
        test_pose,
        position=3,
        mutant_aa="W",
        radius=8.0,
    )

    positions = [
        residue.position
        for residue in context.nearby_residues
    ]

    assert 3 not in positions


def test_nearby_residues_sorted_by_distance(
    test_pose,
):

    context = get_mutation_context(
        test_pose,
        position=3,
        mutant_aa="W",
        radius=20.0,
    )

    distances = [
        residue.distance
        for residue in context.nearby_residues
    ]

    assert distances == sorted(distances)


def test_invalid_position_raises_error(
    test_pose,
):

    with pytest.raises(ValueError):

        get_mutation_context(
            test_pose,
            position=999,
            mutant_aa="W",
        )