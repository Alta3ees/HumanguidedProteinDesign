from fastapi.testclient import TestClient

from human_protein_design.archive import Decision, Design, DesignProject, EvidenceEntry, StructureModel
from human_protein_design.web import api
from human_protein_design.web.design_delete import delete_leaf_design
from human_protein_design.web.design_routes import router as design_router


def _ensure_design_delete_route() -> None:
    if not any(
        getattr(route, "path", None) == "/api/projects/{slug}/designs/{design_id}"
        and "DELETE" in getattr(route, "methods", set())
        for route in api.app.routes
    ):
        api.app.include_router(design_router)


def make_branch(projects_root):
    project = DesignProject(name="demo", root_dir=projects_root / "demo")
    root = Design(name="WT", sequence="ACDEFG", origin="natural_sequence")
    child = Design(
        name="F5W",
        sequence="ACDEWG",
        origin="point_mutation",
        parent_design_id=root.id,
        metadata={"mutation": "F5W"},
    )
    project.archive.add_design(root)
    project.archive.add_design(child)
    project.save()
    return project, root, child


def test_delete_leaf_design_removes_owned_records_and_local_files(tmp_path):
    project, root, child = make_branch(tmp_path / "projects")

    structure_file = project.structures_dir / "child.pdb"
    structure_file.write_text("HEADER TEST\nEND\n", encoding="utf-8")
    structure = StructureModel(
        design_id=child.id,
        structure_path=str(structure_file.relative_to(project.root_dir)),
        source="user",
    )
    project.archive.add_structure(structure)

    evidence_dir = project.evidence_dir / "child"
    evidence_dir.mkdir(parents=True)
    evidence_file = evidence_dir / "result.csv"
    evidence_file.write_text("score\n-1\n", encoding="utf-8")
    evidence = EvidenceEntry(
        source_type="computational",
        source_name="test",
        summary="owned evidence",
        design_id=child.id,
        structure_id=structure.id,
        file_paths=[str(evidence_file.relative_to(project.root_dir))],
    )
    project.archive.add_evidence(evidence)

    decision = Decision(
        parent_design_id=root.id,
        candidate_design_id=child.id,
        outcome="accepted",
        hypothesis="test",
        objective="test",
    )
    project.archive.add_decision(decision)
    project.save()

    result = delete_leaf_design(project, child.id)

    assert result["parent_design_id"] == root.id
    assert child.id not in project.archive.designs
    assert structure.id not in project.archive.structures
    assert evidence.id not in project.archive.evidence
    assert decision.id not in project.archive.decisions
    assert not structure_file.exists()
    assert not evidence_file.exists()
    assert root.id in project.archive.designs

    reloaded = DesignProject.load(name="demo", root_dir=project.root_dir)
    assert child.id not in reloaded.archive.designs
    assert reloaded.archive.get_children(root.id) == []


def test_delete_design_refuses_non_leaf_node(tmp_path):
    project, root, child = make_branch(tmp_path / "projects")

    try:
        delete_leaf_design(project, root.id)
    except ValueError as error:
        message = str(error)
    else:
        raise AssertionError("Expected parent design deletion to be refused")

    assert "child designs" in message
    assert child.id in project.archive.designs
    assert root.id in project.archive.designs


def test_design_delete_api_returns_updated_project(tmp_path, monkeypatch):
    projects_root = tmp_path / "projects"
    project, root, child = make_branch(projects_root)
    monkeypatch.setattr(api, "PROJECTS_ROOT", projects_root)
    _ensure_design_delete_route()
    client = TestClient(api.app)

    response = client.delete(f"/api/projects/demo/designs/{child.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["parent_design_id"] == root.id
    assert payload["project"]["counts"]["designs"] == 1
    assert payload["project"]["design_tree"][0]["id"] == root.id
    assert payload["project"]["design_tree"][0]["children"] == []


def test_design_delete_api_refuses_parent_with_children(tmp_path, monkeypatch):
    projects_root = tmp_path / "projects"
    _, root, _ = make_branch(projects_root)
    monkeypatch.setattr(api, "PROJECTS_ROOT", projects_root)
    _ensure_design_delete_route()
    client = TestClient(api.app)

    response = client.delete(f"/api/projects/demo/designs/{root.id}")

    assert response.status_code == 409
    assert "child designs" in response.json()["detail"]
