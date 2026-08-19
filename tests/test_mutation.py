import pytest

pyrosetta = pytest.importorskip("pyrosetta", reason="PyRosetta is an optional HGD evaluator dependency.")

from human_protein_design.mutation import mutate_pose


@pytest.fixture(scope="module", autouse=True)
def initialize_pyrosetta():
    """Initialize PyRosetta once for this test module."""

    if not pyrosetta.rosetta.basic.was_init_called():
        pyrosetta.init(
            "-mute all "
            "-run:constant_seed "
            "-run:jran 1111111"
        )


@pytest.fixture
def test_pose():
    """Create a small protein pose for mutation tests."""

    return pyrosetta.pose_from_sequence("ACDEFGHIK")


def test_mutate_pose_changes_requested_residue(test_pose):
    mutant_pose = mutate_pose(test_pose, position=3, mutant_aa="W")
    assert mutant_pose.residue(3).name1() == "W"


def test_mutate_pose_preserves_original_pose(test_pose):
    original_sequence = test_pose.sequence()
    mutant_pose = mutate_pose(test_pose, position=3, mutant_aa="W")
    assert test_pose.sequence() == original_sequence
    assert mutant_pose.sequence() != original_sequence


def test_mutate_pose_changes_only_requested_position(test_pose):
    original_sequence = test_pose.sequence()
    mutant_pose = mutate_pose(test_pose, position=3, mutant_aa="W")
    mutant_sequence = mutant_pose.sequence()

    assert len(mutant_sequence) == len(original_sequence)
    for index, (original_aa, mutant_aa) in enumerate(zip(original_sequence, mutant_sequence), start=1):
        if index == 3:
            assert mutant_aa == "W"
        else:
            assert mutant_aa == original_aa
