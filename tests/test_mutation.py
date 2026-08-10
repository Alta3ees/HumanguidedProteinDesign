from src.human_protein_design.mutation import Mutation, apply_mutation


def test_apply_mutation():
    sequence = "ACDEFG"

    mutation = Mutation(
        position=3,
        wild_type="D",
        mutant="W",
    )

    assert apply_mutation(sequence, mutation) == "ACWEFG"


def test_mutation_string():
    mutation = Mutation(
        position=42,
        wild_type="L",
        mutant="F",
    )

    assert str(mutation) == "L42F"


def test_wrong_wild_type():
    sequence = "ACDEFG"

    mutation = Mutation(
        position=3,
        wild_type="A",
        mutant="W",
    )

    try:
        apply_mutation(sequence, mutation)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_same_amino_acid_is_invalid():
    try:
        Mutation(
            position=3,
            wild_type="D",
            mutant="D",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")