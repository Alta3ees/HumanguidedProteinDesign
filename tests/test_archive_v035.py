import pytest

from human_protein_design.archive import (
    Design,
    DesignArchive,
    EvidenceEntry,
    ProjectObjective,
    StructureModel,
    Target,
)


def test_sequence_only_design_is_valid():
    archive = DesignArchive()
    objective = ProjectObjective(description="Understand unknown protein")
    archive.add_objective(objective)
    design = Design(name="WT", sequence="ACDEFG", origin="natural_sequence", objective_id=objective.id)
    archive.add_design(design)
    archive.validate()
    assert design.sequence == "ACDEFG"
    assert archive.get_design_structures(design.id) == []


def test_design_sequence_is_normalized_and_validated_at_model_level():
    design = Design(name="candidate", sequence="ac defg", origin="sequence_design")
    assert design.sequence == "ACDEFG"

    with pytest.raises(ValueError, match="Invalid amino-acid character"):
        Design(name="invalid", sequence="HELLOWORLD", origin="sequence_design")


def test_target_sequence_is_validated_at_model_level():
    target = Target(name="target", sequence="acdefg")
    assert target.sequence == "ACDEFG"

    with pytest.raises(ValueError, match="Invalid amino-acid character"):
        Target(name="invalid target", sequence="ACDX")


def test_de_novo_project_can_exist_before_first_design():
    archive = DesignArchive()
    archive.add_objective(ProjectObjective(description="Design a soluble scaffold", constraints=["Length: 80-100 aa"]))
    archive.validate()
    assert archive.designs == {}


def test_backbone_only_design_and_structure_are_valid():
    archive = DesignArchive()
    design = Design(name="RFdiffusion backbone 001", sequence=None, origin="generated_backbone")
    archive.add_design(design)
    structure = StructureModel(design_id=design.id, structure_path="structures/backbone_001.pdb", source="rfdiffusion", method="RFdiffusion")
    archive.add_structure(structure)
    archive.validate()
    assert design.sequence is None
    assert archive.get_design_structures(design.id) == [structure]


def test_design_can_have_multiple_structural_hypotheses():
    archive = DesignArchive()
    design = Design(name="candidate", sequence="ACDEFG", origin="sequence_design")
    archive.add_design(design)
    archive.add_structure(StructureModel(design_id=design.id, structure_path="structures/af.pdb", source="alphafold"))
    archive.add_structure(StructureModel(design_id=design.id, structure_path="structures/relaxed.pdb", source="rosetta"))
    assert len(archive.get_design_structures(design.id)) == 2


def test_v030_archive_is_migrated_in_memory():
    old = {
        "schema_version": "0.3.0",
        "designs": [{
            "sequence": "ACDEFG",
            "id": "design_old",
            "created_at": "2026-08-17T00:00:00+00:00",
            "parent_design_id": None,
            "status": "active",
            "name": "WT",
            "structure_path": "structures/wt.pdb",
            "metadata": {},
        }],
        "decisions": [],
        "evidence": [],
    }
    archive = DesignArchive.from_dict(old)
    assert archive.get_design("design_old").origin == "imported_design"
    structures = archive.get_design_structures("design_old")
    assert len(structures) == 1
    assert structures[0].structure_path == "structures/wt.pdb"
    assert archive.to_dict()["schema_version"] == "0.3.5"


def test_evidence_can_reference_structure():
    archive = DesignArchive()
    design = Design(name="candidate", origin="imported_design")
    archive.add_design(design)
    structure = StructureModel(design_id=design.id, structure_path="structures/candidate.pdb", source="user")
    archive.add_structure(structure)
    evidence = EvidenceEntry(source_type="computational", source_name="inspection", summary="Structure retained as a hypothesis.", design_id=design.id, structure_id=structure.id)
    archive.add_evidence(evidence)
    archive.validate()
    assert evidence.structure_id == structure.id
