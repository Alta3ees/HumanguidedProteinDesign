"""Persistent archive for protein-design provenance."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from human_protein_design.archive.models import (
    Decision,
    Design,
    EvidenceEntry,
)


class DesignArchive:
    """Persistent collection of designs, decisions, and evidence."""

    def __init__(self) -> None:
        self.designs: dict[str, Design] = {}
        self.decisions: dict[str, Decision] = {}
        self.evidence: dict[str, EvidenceEntry] = {}

    def add_design(self, design: Design) -> None:
        if design.id in self.designs:
            raise ValueError(f"Design already exists: {design.id}")

        if (
            design.parent_design_id is not None
            and design.parent_design_id not in self.designs
        ):
            raise ValueError(
                f"Unknown parent design: {design.parent_design_id}"
            )

        self.designs[design.id] = design

    def add_decision(self, decision: Decision) -> None:
        if decision.id in self.decisions:
            raise ValueError(f"Decision already exists: {decision.id}")

        if decision.parent_design_id not in self.designs:
            raise ValueError(
                f"Unknown parent design: {decision.parent_design_id}"
            )

        if decision.candidate_design_id not in self.designs:
            raise ValueError(
                f"Unknown candidate design: "
                f"{decision.candidate_design_id}"
            )

        self.decisions[decision.id] = decision

    def add_evidence(self, evidence: EvidenceEntry) -> None:
        if evidence.id in self.evidence:
            raise ValueError(f"Evidence already exists: {evidence.id}")

        if evidence.design_id is None and evidence.decision_id is None:
            raise ValueError(
                "Evidence must reference at least one design or decision."
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

    def get_children(self, design_id: str) -> list[Design]:
        """Return direct descendants of a design."""
        return [
            design
            for design in self.designs.values()
            if design.parent_design_id == design_id
        ]

    def get_design_evidence(
        self,
        design_id: str,
    ) -> list[EvidenceEntry]:
        """Return all evidence directly attached to a design."""
        return [
            entry
            for entry in self.evidence.values()
            if entry.design_id == design_id
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "0.3.0",
            "designs": [
                asdict(design)
                for design in self.designs.values()
            ],
            "decisions": [
                asdict(decision)
                for decision in self.decisions.values()
            ],
            "evidence": [
                asdict(entry)
                for entry in self.evidence.values()
            ],
        }

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as handle:
            json.dump(
                self.to_dict(),
                handle,
                indent=2,
                ensure_ascii=False,
            )