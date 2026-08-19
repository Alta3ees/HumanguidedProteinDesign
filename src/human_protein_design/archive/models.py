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

DesignOrigin = Literal[
    "natural_sequence",
    "point_mutation",
    "de_novo",
    "generated_backbone",
    "sequence_design",
    "imported_design",
]

EvidenceSourceType = Literal[
    "computational",
    "experimental",
    "literature",
    "note",
]

StructureSource = Literal[
    "experimental",
    "alphafold",
    "colabfold",
    "rfdiffusion",
    "rosetta",
    "user",
    "other",
]


def utc_now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    """Generate a readable globally unique identifier."""
    return f"{prefix}_{uuid4().hex}"


@dataclass
class ProjectObjective:
    """A scientific objective that may exist before any molecule does."""

    description: str
    constraints: list[str] = field(default_factory=list)

    id: str = field(default_factory=lambda: new_id("objective"))
    created_at: str = field(default_factory=utc_now)

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Target:
    """Optional molecular target, for example in binder design."""

    name: str

    sequence: str | None = None
    structure_path: str | None = None
    notes: str | None = None

    id: str = field(default_factory=lambda: new_id("target"))
    created_at: str = field(default_factory=utc_now)

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StructureModel:
    """A structural hypothesis associated with a design.

    A design can have zero, one, or many structure models. Structure provenance
    and confidence are retained separately from the molecular design itself.
    """

    design_id: str
    structure_path: str
    source: StructureSource

    method: str | None = None

    id: str = field(default_factory=lambda: new_id("structure"))
    created_at: str = field(default_factory=utc_now)

    mean_plddt: float | None = None
    ptm: float | None = None
    iptm: float | None = None
    pae_path: str | None = None

    notes: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Design:
    """A protein design represented as a node in the design tree.

    v0.3.5 makes sequence optional. This supports backbone-only de novo designs
    and lets projects exist before a sequence or trusted structure is available.

    `structure_path` is kept as a legacy compatibility field for v0.3 archives.
    New code should prefer first-class StructureModel records.
    """

    sequence: str | None = None

    id: str = field(default_factory=lambda: new_id("design"))
    created_at: str = field(default_factory=utc_now)

    parent_design_id: str | None = None

    status: DesignStatus = "active"
    origin: DesignOrigin = "imported_design"

    name: str | None = None

    # Legacy v0.3 compatibility. Prefer StructureModel in new workflows.
    structure_path: str | None = None

    objective_id: str | None = None
    target_id: str | None = None

    hypothesis: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.sequence is not None:
            normalized = "".join(self.sequence.split()).upper()
            self.sequence = normalized or None

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
    """A dated piece of evidence associated with scientific archive records."""

    source_type: EvidenceSourceType
    source_name: str

    summary: str

    design_id: str | None = None
    decision_id: str | None = None
    structure_id: str | None = None
    target_id: str | None = None

    id: str = field(default_factory=lambda: new_id("evidence"))
    created_at: str = field(default_factory=utc_now)

    data: dict[str, Any] = field(default_factory=dict)

    file_paths: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)

    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
