"""Core scientific provenance models for Human-Guided Protein Design."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4


DecisionOutcome = Literal["accepted", "rejected", "deferred"]

DesignStatus = Literal[
    "active",
    "deprioritized",
    "superseded",
]

EvidenceSourceType = Literal[
    "rosetta",
    "structure_inspection",
    "computational",
    "experiment",
    "literature",
    "note",
]


def utc_now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    """Generate a readable globally unique identifier."""
    return f"{prefix}_{uuid4().hex}"


@dataclass
class Design:
    """A protein design represented as a node in the design tree."""

    sequence: str

    id: str = field(default_factory=lambda: new_id("design"))
    created_at: str = field(default_factory=utc_now)

    parent_design_id: str | None = None

    status: DesignStatus = "active"

    structure_path: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Decision:
    """A human scientific decision concerning a candidate design."""

    parent_design_id: str
    candidate_design_id: str

    outcome: DecisionOutcome

    hypothesis: str
    objective: str

    rationale: str | None = None

    id: str = field(default_factory=lambda: new_id("decision"))
    created_at: str = field(default_factory=utc_now)

    program_comment: str | None = None
    user_note: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceEntry:
    """A dated piece of evidence associated with a design or decision."""

    source_type: EvidenceSourceType
    source_name: str

    summary: str

    design_id: str | None = None
    decision_id: str | None = None

    id: str = field(default_factory=lambda: new_id("evidence"))
    created_at: str = field(default_factory=utc_now)

    data: dict[str, Any] = field(default_factory=dict)

    file_paths: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)

    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)