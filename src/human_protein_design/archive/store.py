"""Persistent archive for protein-design provenance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from human_protein_design.archive.models import (
    Decision,
    Design,
    EvidenceEntry,
    ProjectObjective,
    StructureModel,
    Target,
)


class DesignArchive:
    """Persistent collection of designs, decisions, structures, targets, and evidence."""

    SCHEMA_VERSION = "0.3.5"
    LEGACY_SCHEMA_VERSIONS = {"0.3.0"}

    def __init__(self) -> None:
        self.designs: dict[str, Design] = {}
        self.decisions: dict[str, Decision] = {}
        self.evidence: dict[str, EvidenceEntry] = {}
        self.structures: dict[str, StructureModel] = {}
        self.objectives: dict[str, ProjectObjective] = {}
        self.targets: dict[str, Target] = {}

    def add_objective(self, objective: ProjectObjective) -> None:
        if objective.id in self.objectives:
            raise ValueError(f"Objective already exists: {objective.id}")
        self.objectives[objective.id] = objective

    def add_target(self, target: Target) -> None:
        if target.id in self.targets:
            raise ValueError(f"Target already exists: {target.id}")
        self.targets[target.id] = target

    def add_design(self, design: Design) -> None:
        if design.id in self.designs:
            raise ValueError(f"Design already exists: {design.id}")
        if design.parent_design_id is not None and design.parent_design_id not in self.designs:
            raise ValueError(f"Unknown parent design: {design.parent_design_id}")
        if design.objective_id is not None and design.objective_id not in self.objectives:
            raise ValueError(f"Unknown objective: {design.objective_id}")
        if design.target_id is not None and design.target_id not in self.targets:
            raise ValueError(f"Unknown target: {design.target_id}")
        self.designs[design.id] = design

    def add_structure(self, structure: StructureModel) -> None:
        if structure.id in self.structures:
            raise ValueError(f"Structure already exists: {structure.id}")
        if structure.design_id not in self.designs:
            raise ValueError(f"Unknown design: {structure.design_id}")
        self.structures[structure.id] = structure

    def add_decision(self, decision: Decision) -> None:
        if decision.id in self.decisions:
            raise ValueError(f"Decision already exists: {decision.id}")
        if decision.parent_design_id not in self.designs:
            raise ValueError(f"Unknown parent design: {decision.parent_design_id}")
        if decision.candidate_design_id not in self.designs:
            raise ValueError(f"Unknown candidate design: {decision.candidate_design_id}")
        self.decisions[decision.id] = decision

    def add_evidence(self, evidence: EvidenceEntry) -> None:
        if evidence.id in self.evidence:
            raise ValueError(f"Evidence already exists: {evidence.id}")
        if not any((evidence.design_id, evidence.decision_id, evidence.structure_id, evidence.target_id)):
            raise ValueError("Evidence must reference at least one design, decision, structure, or target.")
        if evidence.design_id is not None and evidence.design_id not in self.designs:
            raise ValueError(f"Unknown design: {evidence.design_id}")
        if evidence.decision_id is not None and evidence.decision_id not in self.decisions:
            raise ValueError(f"Unknown decision: {evidence.decision_id}")
        if evidence.structure_id is not None and evidence.structure_id not in self.structures:
            raise ValueError(f"Unknown structure: {evidence.structure_id}")
        if evidence.target_id is not None and evidence.target_id not in self.targets:
            raise ValueError(f"Unknown target: {evidence.target_id}")
        self.evidence[evidence.id] = evidence

    def get_design(self, design_id: str) -> Design:
        try:
            return self.designs[design_id]
        except KeyError as error:
            raise KeyError(f"Unknown design: {design_id}") from error

    def get_structure(self, structure_id: str) -> StructureModel:
        try:
            return self.structures[structure_id]
        except KeyError as error:
            raise KeyError(f"Unknown structure: {structure_id}") from error

    def get_children(self, design_id: str) -> list[Design]:
        return [design for design in self.designs.values() if design.parent_design_id == design_id]

    def get_root_designs(self) -> list[Design]:
        return [design for design in self.designs.values() if design.parent_design_id is None]

    def get_design_structures(self, design_id: str) -> list[StructureModel]:
        structures = [structure for structure in self.structures.values() if structure.design_id == design_id]
        return sorted(structures, key=lambda structure: structure.created_at)

    def get_design_decisions(self, design_id: str) -> list[Decision]:
        decisions = [decision for decision in self.decisions.values() if decision.candidate_design_id == design_id]
        return sorted(decisions, key=lambda decision: decision.created_at)

    def get_latest_decision(self, design_id: str) -> Decision | None:
        decisions = self.get_design_decisions(design_id)
        return decisions[-1] if decisions else None

    def get_design_evidence(self, design_id: str) -> list[EvidenceEntry]:
        evidence = [entry for entry in self.evidence.values() if entry.design_id == design_id]
        return sorted(evidence, key=lambda entry: entry.created_at)

    def get_decision_evidence(self, decision_id: str) -> list[EvidenceEntry]:
        evidence = [entry for entry in self.evidence.values() if entry.decision_id == decision_id]
        return sorted(evidence, key=lambda entry: entry.created_at)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "objectives": [item.to_dict() for item in self.objectives.values()],
            "targets": [item.to_dict() for item in self.targets.values()],
            "designs": [item.to_dict() for item in self.designs.values()],
            "structures": [item.to_dict() for item in self.structures.values()],
            "decisions": [item.to_dict() for item in self.decisions.values()],
            "evidence": [item.to_dict() for item in self.evidence.values()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DesignArchive":
        schema_version = data.get("schema_version")
        if schema_version not in {cls.SCHEMA_VERSION, *cls.LEGACY_SCHEMA_VERSIONS}:
            raise ValueError(
                "Unsupported archive schema version: "
                f"{schema_version!r}. Expected {cls.SCHEMA_VERSION!r} "
                f"or one of {sorted(cls.LEGACY_SCHEMA_VERSIONS)!r}."
            )

        archive = cls()

        for objective_data in data.get("objectives", []):
            objective = ProjectObjective(**objective_data)
            archive.objectives[objective.id] = objective
        for target_data in data.get("targets", []):
            target = Target(**target_data)
            archive.targets[target.id] = target
        for design_data in data.get("designs", []):
            payload = dict(design_data)
            if schema_version == "0.3.0":
                payload.setdefault("origin", "point_mutation" if payload.get("parent_design_id") else "imported_design")
            design = Design(**payload)
            archive.designs[design.id] = design
        for structure_data in data.get("structures", []):
            structure = StructureModel(**structure_data)
            archive.structures[structure.id] = structure

        if schema_version == "0.3.0":
            for design in archive.designs.values():
                if design.structure_path:
                    structure = StructureModel(
                        design_id=design.id,
                        structure_path=design.structure_path,
                        source="user",
                        method="migrated from v0.3 structure_path",
                        metadata={"migrated_from": "0.3.0"},
                    )
                    archive.structures[structure.id] = structure

        for decision_data in data.get("decisions", []):
            decision = Decision(**decision_data)
            archive.decisions[decision.id] = decision
        for evidence_data in data.get("evidence", []):
            evidence = EvidenceEntry(**evidence_data)
            archive.evidence[evidence.id] = evidence

        archive.validate()
        return archive

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.validate()
        temporary_path = path.with_suffix(path.suffix + ".tmp")
        with temporary_path.open("w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        temporary_path.replace(path)

    @classmethod
    def load(cls, path: str | Path) -> "DesignArchive":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Archive does not exist: {path}")
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return cls.from_dict(data)

    def validate(self) -> None:
        for design in self.designs.values():
            if design.parent_design_id is not None and design.parent_design_id not in self.designs:
                raise ValueError(f"Design {design.id} references missing parent {design.parent_design_id}.")
            if design.objective_id is not None and design.objective_id not in self.objectives:
                raise ValueError(f"Design {design.id} references missing objective {design.objective_id}.")
            if design.target_id is not None and design.target_id not in self.targets:
                raise ValueError(f"Design {design.id} references missing target {design.target_id}.")
        for structure in self.structures.values():
            if structure.design_id not in self.designs:
                raise ValueError(f"Structure {structure.id} references missing design {structure.design_id}.")
        for decision in self.decisions.values():
            if decision.parent_design_id not in self.designs:
                raise ValueError(f"Decision {decision.id} references missing parent design {decision.parent_design_id}.")
            if decision.candidate_design_id not in self.designs:
                raise ValueError(f"Decision {decision.id} references missing candidate design {decision.candidate_design_id}.")
        for evidence in self.evidence.values():
            if evidence.design_id is not None and evidence.design_id not in self.designs:
                raise ValueError(f"Evidence {evidence.id} references missing design {evidence.design_id}.")
            if evidence.decision_id is not None and evidence.decision_id not in self.decisions:
                raise ValueError(f"Evidence {evidence.id} references missing decision {evidence.decision_id}.")
            if evidence.structure_id is not None and evidence.structure_id not in self.structures:
                raise ValueError(f"Evidence {evidence.id} references missing structure {evidence.structure_id}.")
            if evidence.target_id is not None and evidence.target_id not in self.targets:
                raise ValueError(f"Evidence {evidence.id} references missing target {evidence.target_id}.")

    def get_lineage(self, design_id: str) -> list[Design]:
        lineage: list[Design] = []
        current = self.get_design(design_id)
        visited: set[str] = set()
        while True:
            if current.id in visited:
                raise ValueError(f"Cycle detected in design lineage at {current.id}.")
            visited.add(current.id)
            lineage.append(current)
            if current.parent_design_id is None:
                break
            current = self.get_design(current.parent_design_id)
        lineage.reverse()
        return lineage

    def get_lineage_mutations(self, design_id: str) -> list[str]:
        mutations: list[str] = []
        for design in self.get_lineage(design_id):
            mutation = design.metadata.get("mutation")
            if mutation:
                mutations.append(str(mutation))
        return mutations

    def get_lineage_label(self, design_id: str) -> str:
        lineage = self.get_lineage(design_id)
        labels: list[str] = []
        for index, design in enumerate(lineage):
            mutation = design.metadata.get("mutation")
            if index == 0:
                labels.append(design.name or "WT")
                continue
            if mutation is None:
                labels.append(design.name or design.id[:12])
                continue
            labels.append(str(mutation) if index == 1 else f"+{mutation}")
        return " -> ".join(labels)

    def get_decision_outcome(self, design_id: str) -> str | None:
        decision = self.get_latest_decision(design_id)
        return decision.outcome if decision is not None else None

    def get_design_evidence_counts(self, design_id: str) -> dict[str, int]:
        counts = {"computational": 0, "experimental": 0, "literature": 0, "note": 0}
        for entry in self.get_design_evidence(design_id):
            counts[entry.source_type] = counts.get(entry.source_type, 0) + 1
        return counts

    def get_design_label(self, design_id: str) -> str:
        design = self.get_design(design_id)
        if design.name:
            return design.name
        mutation = design.metadata.get("mutation")
        if mutation:
            return str(mutation)
        if design.parent_design_id is None:
            return "WT"
        return design.id[:12]

    def get_rosetta_delta_score(self, design_id: str) -> float | None:
        rosetta_entries = [
            entry
            for entry in self.get_design_evidence(design_id)
            if entry.source_type == "computational" and entry.source_name.lower() == "pyrosetta"
        ]
        if not rosetta_entries:
            return None
        value = rosetta_entries[-1].data.get("delta_score")
        return float(value) if isinstance(value, (int, float)) else None
