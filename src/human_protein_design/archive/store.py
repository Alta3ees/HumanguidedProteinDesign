"""Persistent archive for protein-design provenance."""

from __future__ import annotations

import json

from pathlib import Path
from typing import Any

from human_protein_design.archive.models import (
    Decision,
    Design,
    EvidenceEntry,
)


class DesignArchive:
    """Persistent collection of designs, decisions, and evidence."""

    SCHEMA_VERSION = "0.3.0"

    def __init__(self) -> None:
        self.designs: dict[str, Design] = {}
        self.decisions: dict[str, Decision] = {}
        self.evidence: dict[str, EvidenceEntry] = {}

    # ============================================================
    # Add records
    # ============================================================

    def add_design(
        self,
        design: Design,
    ) -> None:
        """Add a design to the archive."""

        if design.id in self.designs:
            raise ValueError(
                f"Design already exists: {design.id}"
            )

        if (
            design.parent_design_id is not None
            and design.parent_design_id not in self.designs
        ):
            raise ValueError(
                "Unknown parent design: "
                f"{design.parent_design_id}"
            )

        self.designs[design.id] = design

    def add_decision(
        self,
        decision: Decision,
    ) -> None:
        """Append a scientific decision to the archive."""

        if decision.id in self.decisions:
            raise ValueError(
                f"Decision already exists: {decision.id}"
            )

        if decision.parent_design_id not in self.designs:
            raise ValueError(
                "Unknown parent design: "
                f"{decision.parent_design_id}"
            )

        if decision.candidate_design_id not in self.designs:
            raise ValueError(
                "Unknown candidate design: "
                f"{decision.candidate_design_id}"
            )

        self.decisions[decision.id] = decision

    def add_evidence(
        self,
        evidence: EvidenceEntry,
    ) -> None:
        """Append evidence to the archive."""

        if evidence.id in self.evidence:
            raise ValueError(
                f"Evidence already exists: {evidence.id}"
            )

        if (
            evidence.design_id is None
            and evidence.decision_id is None
        ):
            raise ValueError(
                "Evidence must reference at least "
                "one design or decision."
            )

        if (
            evidence.design_id is not None
            and evidence.design_id not in self.designs
        ):
            raise ValueError(
                f"Unknown design: {evidence.design_id}"
            )

        if (
            evidence.decision_id is not None
            and evidence.decision_id not in self.decisions
        ):
            raise ValueError(
                f"Unknown decision: {evidence.decision_id}"
            )

        self.evidence[evidence.id] = evidence

    # ============================================================
    # Design-tree queries
    # ============================================================

    def get_design(
        self,
        design_id: str,
    ) -> Design:
        """Return one design."""

        try:
            return self.designs[design_id]
        except KeyError as error:
            raise KeyError(
                f"Unknown design: {design_id}"
            ) from error

    def get_children(
        self,
        design_id: str,
    ) -> list[Design]:
        """Return direct descendants of a design."""

        return [
            design
            for design in self.designs.values()
            if design.parent_design_id == design_id
        ]

    def get_root_designs(
        self,
    ) -> list[Design]:
        """Return designs with no parent."""

        return [
            design
            for design in self.designs.values()
            if design.parent_design_id is None
        ]

    # ============================================================
    # Decision history
    # ============================================================

    def get_design_decisions(
        self,
        design_id: str,
    ) -> list[Decision]:
        """
        Return all decisions ever made about a design.

        Decisions are ordered chronologically.
        """

        decisions = [
            decision
            for decision in self.decisions.values()
            if decision.candidate_design_id == design_id
        ]

        return sorted(
            decisions,
            key=lambda decision: decision.created_at,
        )

    def get_latest_decision(
        self,
        design_id: str,
    ) -> Decision | None:
        """Return the most recent decision for a design."""

        decisions = self.get_design_decisions(
            design_id
        )

        if not decisions:
            return None

        return decisions[-1]

    # ============================================================
    # Evidence history
    # ============================================================

    def get_design_evidence(
        self,
        design_id: str,
    ) -> list[EvidenceEntry]:
        """
        Return all evidence attached to a design.

        Evidence is ordered chronologically.
        """

        evidence = [
            entry
            for entry in self.evidence.values()
            if entry.design_id == design_id
        ]

        return sorted(
            evidence,
            key=lambda entry: entry.created_at,
        )

    def get_decision_evidence(
        self,
        decision_id: str,
    ) -> list[EvidenceEntry]:
        """Return evidence attached to a decision."""

        evidence = [
            entry
            for entry in self.evidence.values()
            if entry.decision_id == decision_id
        ]

        return sorted(
            evidence,
            key=lambda entry: entry.created_at,
        )

    # ============================================================
    # Serialization
    # ============================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """Convert the complete archive to a dictionary."""

        return {
            "schema_version": self.SCHEMA_VERSION,
            "designs": [
                design.to_dict()
                for design in self.designs.values()
            ],
            "decisions": [
                decision.to_dict()
                for decision in self.decisions.values()
            ],
            "evidence": [
                entry.to_dict()
                for entry in self.evidence.values()
            ],
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> DesignArchive:
        """Reconstruct an archive from serialized data."""

        schema_version = data.get(
            "schema_version"
        )

        if schema_version != cls.SCHEMA_VERSION:
            raise ValueError(
                "Unsupported archive schema version: "
                f"{schema_version!r}. "
                f"Expected {cls.SCHEMA_VERSION!r}."
            )

        archive = cls()

        # Designs must be loaded first because decisions
        # and evidence may reference them.
        for design_data in data.get(
            "designs",
            [],
        ):
            design = Design(
                **design_data
            )

            archive.designs[
                design.id
            ] = design

        for decision_data in data.get(
            "decisions",
            [],
        ):
            decision = Decision(
                **decision_data
            )

            archive.decisions[
                decision.id
            ] = decision

        for evidence_data in data.get(
            "evidence",
            [],
        ):
            evidence = EvidenceEntry(
                **evidence_data
            )

            archive.evidence[
                evidence.id
            ] = evidence

        archive.validate()

        return archive

    # ============================================================
    # Disk persistence
    # ============================================================

    def save(
        self,
        path: str | Path,
    ) -> None:
        """Save the complete archive to JSON."""

        path = Path(path)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with path.open(
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                self.to_dict(),
                handle,
                indent=2,
                ensure_ascii=False,
            )

    @classmethod
    def load(
        cls,
        path: str | Path,
    ) -> DesignArchive:
        """Load a persistent archive from JSON."""

        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(
                f"Archive does not exist: {path}"
            )

        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            data = json.load(
                handle
            )

        return cls.from_dict(
            data
        )

    # ============================================================
    # Integrity checks
    # ============================================================

    def validate(
        self,
    ) -> None:
        """Check relationships between archive records."""

        for design in self.designs.values():

            if design.parent_design_id is None:
                continue

            if (
                design.parent_design_id
                not in self.designs
            ):
                raise ValueError(
                    f"Design {design.id} references "
                    "missing parent "
                    f"{design.parent_design_id}."
                )

        for decision in self.decisions.values():

            if (
                decision.parent_design_id
                not in self.designs
            ):
                raise ValueError(
                    f"Decision {decision.id} references "
                    "missing parent design "
                    f"{decision.parent_design_id}."
                )

            if (
                decision.candidate_design_id
                not in self.designs
            ):
                raise ValueError(
                    f"Decision {decision.id} references "
                    "missing candidate design "
                    f"{decision.candidate_design_id}."
                )

        for evidence in self.evidence.values():

            if (
                evidence.design_id is not None
                and evidence.design_id
                not in self.designs
            ):
                raise ValueError(
                    f"Evidence {evidence.id} references "
                    "missing design "
                    f"{evidence.design_id}."
                )

            if (
                evidence.decision_id is not None
                and evidence.decision_id
                not in self.decisions
            ):
                raise ValueError(
                    f"Evidence {evidence.id} references "
                    "missing decision "
                    f"{evidence.decision_id}."
                )
    def get_lineage(
        self,
        design_id: str,
    ) -> list[Design]:
        """
        Return the complete lineage from root to design.

        Example:
            WT -> L5W -> +L7N -> +F30Y
        """

        lineage: list[Design] = []

        current = self.get_design(
            design_id
        )

        visited: set[str] = set()

        while True:

            if current.id in visited:
                raise ValueError(
                    "Cycle detected in design lineage at "
                    f"{current.id}."
                )

            visited.add(
                current.id
            )

            lineage.append(
                current
            )

            if current.parent_design_id is None:
                break

            current = self.get_design(
                current.parent_design_id
            )

        lineage.reverse()

        return lineage


    def get_lineage_mutations(
        self,
        design_id: str,
    ) -> list[str]:
        """
        Return mutations accumulated from root to design.
        """

        lineage = self.get_lineage(
            design_id
        )

        mutations: list[str] = []

        for design in lineage:

            mutation = design.metadata.get(
                "mutation"
            )

            if mutation:
                mutations.append(
                    str(mutation)
                )

        return mutations


    def get_lineage_label(
        self,
        design_id: str,
    ) -> str:
        """
        Return a compact human-readable lineage.

        Example:
            WT -> L5W -> +L7N
        """

        lineage = self.get_lineage(
            design_id
        )

        labels: list[str] = []

        for index, design in enumerate(
            lineage
        ):

            mutation = design.metadata.get(
                "mutation"
            )

            if index == 0:
                labels.append(
                    "WT"
                )
                continue

            if mutation is None:
                labels.append(
                    design.id[:12]
                )
                continue

            if index == 1:
                labels.append(
                    str(mutation)
                )
            else:
                labels.append(
                    f"+{mutation}"
                )

        return " -> ".join(
            labels
        )
    
    def get_decision_outcome(
        self,
        design_id: str,
    ) -> str | None:
        """Return the latest decision outcome for a design."""

        decision = self.get_latest_decision(
            design_id
        )

        if decision is None:
            return None

        return decision.outcome


    def get_design_evidence_counts(
        self,
        design_id: str,
    ) -> dict[str, int]:
        """Count evidence entries by type."""

        counts = {
            "computational": 0,
            "experimental": 0,
            "literature": 0,
            "note": 0,
        }

        for entry in self.get_design_evidence(
            design_id
        ):

            counts[
                entry.source_type
            ] = (
                counts.get(
                    entry.source_type,
                    0,
                )
                + 1
            )

        return counts


    def get_design_label(
        self,
        design_id: str,
    ) -> str:
        """Return a concise human-readable design label."""

        design = self.get_design(
            design_id
        )

        if design.name:
            return design.name

        mutation = design.metadata.get(
            "mutation"
        )

        if mutation:
            return str(
                mutation
            )

        if design.parent_design_id is None:
            return "WT"

        return design.id[:12]


    def get_rosetta_delta_score(
        self,
        design_id: str,
    ) -> float | None:
        """Return the most recent Rosetta ΔScore for a design."""

        evidence = self.get_design_evidence(
            design_id
        )

        rosetta_entries = [
            entry
            for entry in evidence
            if (
                entry.source_type
                == "computational"
                and entry.source_name.lower()
                == "pyrosetta"
            )
        ]

        if not rosetta_entries:
            return None

        latest = rosetta_entries[-1]

        value = latest.data.get(
            "delta_score"
        )

        if isinstance(
            value,
            (int, float),
        ):
            return float(
                value
            )

        return None