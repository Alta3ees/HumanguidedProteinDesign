from fastapi.testclient import TestClient

from human_protein_design.archive import Design, DesignProject, EvidenceEntry, ProjectObjective, StructureModel
from human_protein_design.web import api


def test_project_api_exposes_design_tree(tmp_path, monkeypatch):
    projects_root = tmp_path / "projects"
    project_dir = projects_root / "demo"
    project = DesignProject(name="demo", root_dir=project_dir)

    objective = ProjectObjective(description="Explore a candidate protein")
    project.archive.add_objective(objective)

    root = Design(name="WT", sequence="ACDEFG", origin="natural_sequence", objective_id=objective.id)
    project.archive.add_design(root)
    child = Design(
        name="WT -> F6W",
        sequence="ACDEWG",
        origin="point_mutation",
        parent_design_id=root.id,
        objective_id=objective.id,
        metadata={"mutation": "F6W"},
    )
    project.archive.add_design(child)
    structure = StructureModel(
        design_id=child.id,
        structure_path="structures/child.pdb",
        source="alphafold",
        mean_plddt=91.2,
    )
    project.archive.add_structure(structure)
    project.archive.add_evidence(
        EvidenceEntry(
            source_type="computational",
            source_name="AlphaFold",
            summary="High-confidence structural hypothesis.",
            design_id=child.id,
            structure_id=structure.id,
        )
    )
    project.save()

    monkeypatch.setattr(api, "PROJECTS_ROOT", projects_root)
    client = TestClient(api.app)

    listing = client.get("/api/projects")
    assert listing.status_code == 200
    assert listing.json()[0]["slug"] == "demo"

    response = client.get("/api/projects/demo")
    assert response.status_code == 200
    payload = response.json()
    assert payload["counts"]["designs"] == 2
    assert payload["design_tree"][0]["label"] == "WT"
    assert payload["design_tree"][0]["children"][0]["id"] == child.id
    assert payload["design_tree"][0]["children"][0]["structures"][0]["source"] == "alphafold"
    assert payload["design_tree"][0]["children"][0]["evidence_counts"]["computational"] == 1


def test_project_api_rejects_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "PROJECTS_ROOT", tmp_path)
    client = TestClient(api.app)
    response = client.get("/api/projects/..%5Csecret")
    assert response.status_code == 400
