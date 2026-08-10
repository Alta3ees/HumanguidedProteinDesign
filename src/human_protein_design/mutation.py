"""Utilities for working with protein sequences and mutations."""

from dataclasses import dataclass


STANDARD_AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"


@dataclass(frozen=True)
class Mutation:
    """Represent a single amino-acid substitution."""

    position: int
    wild_type: str
    mutant: str

    def __post_init__(self) -> None:
        if self.position < 1:
            raise ValueError("Protein positions must be 1-indexed and positive.")

        if self.wild_type not in STANDARD_AMINO_ACIDS:
            raise ValueError(f"Invalid wild-type amino acid: {self.wild_type}")

        if self.mutant not in STANDARD_AMINO_ACIDS:
            raise ValueError(f"Invalid mutant amino acid: {self.mutant}")

        if self.wild_type == self.mutant:
            raise ValueError("Wild-type and mutant amino acids must differ.")

    def __str__(self) -> str:
        """Return standard mutation notation, e.g. L42F."""
        return f"{self.wild_type}{self.position}{self.mutant}"


def apply_mutation(sequence: str, mutation: Mutation) -> str:
    """Apply a single mutation to a protein sequence.

    Positions are 1-indexed, following standard biological notation.
    """
    sequence = sequence.upper()

    if mutation.position > len(sequence):
        raise ValueError(
            f"Position {mutation.position} is outside the sequence "
            f"(length={len(sequence)})."
        )

    current_residue = sequence[mutation.position - 1]

    if current_residue != mutation.wild_type:
        raise ValueError(
            f"Expected {mutation.wild_type} at position {mutation.position}, "
            f"found {current_residue}."
        )

    sequence_list = list(sequence)
    sequence_list[mutation.position - 1] = mutation.mutant

    return "".join(sequence_list)