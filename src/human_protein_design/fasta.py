"""Minimal FASTA utilities for sequence-only project initialization."""

from __future__ import annotations

from pathlib import Path

VALID_AA = set("ACDEFGHIKLMNPQRSTVWYXBZUOJ")


def normalize_sequence(sequence: str) -> str:
    """Normalize and validate a protein sequence."""
    normalized = "".join(sequence.split()).upper()
    if not normalized:
        raise ValueError("Protein sequence is empty.")
    invalid = sorted(set(normalized) - VALID_AA)
    if invalid:
        raise ValueError("Invalid protein-sequence character(s): " + ", ".join(invalid))
    return normalized


def read_single_fasta(path: str | Path) -> tuple[str, str]:
    """Read one sequence from a FASTA file."""
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
