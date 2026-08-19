"""Minimal FASTA and protein-sequence validation utilities."""

from __future__ import annotations

from pathlib import Path

# HGD v0.3.5 intentionally accepts only the 20 canonical proteinogenic
# amino-acid one-letter codes. Ambiguous/noncanonical symbols such as X, B, Z,
# J, U, and O must be handled explicitly in a future feature rather than being
# silently accepted into designs that downstream tools may not support.
VALID_AMINO_ACIDS = frozenset("ACDEFGHIKLMNPQRSTVWY")


def normalize_sequence(sequence: str) -> str:
    """Normalize and validate a protein sequence.

    Whitespace is removed and lowercase letters are converted to uppercase.
    A ValueError is raised for an empty sequence or for any character outside
    the 20 canonical amino-acid one-letter codes.
    """
    normalized = "".join(sequence.split()).upper()
    if not normalized:
        raise ValueError("Protein sequence is empty.")

    invalid = sorted(set(normalized) - VALID_AMINO_ACIDS)
    if invalid:
        raise ValueError(
            "Invalid amino-acid character(s): "
            + ", ".join(invalid)
            + ". Allowed: "
            + "".join(sorted(VALID_AMINO_ACIDS))
        )

    return normalized


def validate_amino_acid(amino_acid: str) -> str:
    """Normalize and validate one canonical amino-acid code."""
    normalized = amino_acid.strip().upper()
    if len(normalized) != 1 or normalized not in VALID_AMINO_ACIDS:
        raise ValueError(
            f"Invalid amino acid: {amino_acid!r}. "
            "Enter one standard amino-acid code "
            f"({''.join(sorted(VALID_AMINO_ACIDS))})."
        )
    return normalized


def read_single_fasta(path: str | Path) -> tuple[str, str]:
    """Read and validate one sequence from a FASTA file."""
    path = Path(path)
    header: str | None = None
    sequence_parts: list[str] = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if header is not None:
                raise ValueError("Expected a single-sequence FASTA file.")
            header = line[1:].strip() or path.stem
            continue
        sequence_parts.append(line)

    if not sequence_parts:
        raise ValueError(f"No sequence found in {path}")

    return header or path.stem, normalize_sequence("".join(sequence_parts))
