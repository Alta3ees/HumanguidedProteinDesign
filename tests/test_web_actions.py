from fastapi.testclient import TestClient

from human_protein_design.archive import Design, DesignProject, EvidenceEntry
from human_protein_design.web import api


def make_project(projects_root):
    project = DesignProject(name="demo", root_dir=projects_root / "demo")
    root = Design(name="WT", sequence="ACDEFG", origin="natural_sequence")
    project.archive.add_design(root)
    project.save()
    return project, root


def test_create_project_from_web(tmp_path, monkeypatch):
    projects_root = tmp_path / "projects"
    monkeypatch.setattr(api, "PROJECTS_ROOT", projects_root)
    client = TestClient(api.app)

    response = client.post(
        "/api/projects",
        json={
            "name": "Sequence project",
            "objective": "Explore sequence variants",
            "sequence": "ACDEFG",
            "design_name": "start",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["counts"]["designs"] == 1
    assert payload["project"]["design_tree"][0]["sequence"] == "ACDEFG"
    assert (projects_root / "sequence_project" / "design_archive.json").is_file()


def test_sequence_editor_creates_child_without_rewriting_parent(tmp_path, monkeypatch):
    projects_root = tmp_path / "projects"
    project, root = make_project(projects_root)
    monkeypatch.setattr(api, "PROJECTS_ROOT", projects_root)
    client = TestClient(api.app)

    response = client.post(
        f"/api/projects/demo/designs/{root.id}/derive-sequence",
        json={"sequence": "ACDEWG", "name": "F5W edit", "hypothesis": "test edit"},
    )

    assert response.status_code == 200
    payload = response.json()
    child_id = payload["design_id"]

    reloaded = DesignProject.load(name="demo", root_dir=projects_root / "demo")
    assert reloaded.archive.designs[root.id].sequence == "ACDEFG"
    child = reloaded.archive.designs[child_id]
    assert child.parent_design_id == root.id
    assert child.sequence == "ACDEWG"
    assert child.origin == "sequence_design"
    assert child.metadata["sequence_changes"] == [{"position": 5, "from": "F", "to": "W"}]


def test_register_design_from_web(tmp_path, monkeypatch):
    projects_root = tmp_path / "projects"
    _, root = make_project(projects_root)
    monkeypatch.setattr(api, "PROJECTS_ROOT", projects_root)
    client = TestClient(api.app)

    response = client.post(
        "/api/projects/demo/designs",
        json={
            "name": "MPNN candidate",
            "origin": "sequence_design",
            "sequence": "ACDEFA",
            "parent_design_id": root.id,
            "source_tool": "ProteinMPNN",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["counts"]["designs"] == 2
    assert payload["project"]["counts"]["evidence"] == 1


def test_attach_structure_from_web(tmp_path, monkeypatch):
    projects_root = tmp_path / "projects"
    _, root = make_project(projects_root)
    monkeypatch.setattr(api, "PROJECTS_ROOT", projects_root)
    client = TestClient(api.app)

    response = client.post(
        f"/api/projects/demo/designs/{root.id}/structures",
        data={"source": "alphafold", "method": "AF test", "mean_plddt": "91.4"},
        files={"file": ("model.pdb", b"HEADER TEST\nEND\n", "chemical/x-pdb")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["counts"]["structures"] == 1
    assert payload["project"]["counts"]["evidence"] == 1
    assert (projects_root / "demo" / "structures" / "model.pdb").is_file()


def test_delete_imported_evidence_removes_evidence_file(tmp_path, monkeypatch):
    projects_root = tmp_path / "projects"
    project, root = make_project(projects_root)
    evidence_dir = project.evidence_dir / "import_test"
    evidence_dir.mkdir(parents=True)
    evidence_file = evidence_dir / "spectrum.ucsf"
    evidence_file.write_bytes(b"data")
    entry = EvidenceEntry(
        source_type="experimental",
        source_name="NMR",
        summary="test",
        design_id=root.id,
        file_paths=[str(evidence_file.relative_to(project.root_dir))],
    )
    project.archive.add_evidence(entry)
    project.save()

    monkeypatch.setattr(api, "PROJECTS_ROOT", projects_root)
    client = TestClient(api.app)
    response = client.delete(f"/api/projects/demo/evidence/{entry.id}")

    assert response.status_code == 200
    assert not evidence_file.exists()
    reloaded = DesignProject.load(name="demo", root_dir=projects_root / "demo")
    assert entry.id not in reloaded.archive.evidence


def test_delete_evidence_never_deletes_structure_file(tmp_path, monkeypatch):
    projects_root = tmp_path / "projects"
    project, root = make_project(projects_root)
    structure_file = project.structures_dir / "model.pdb"
    structure_file.write_text("HEADER TEST\nEND\n", encoding="utf-8")
    entry = EvidenceEntry(
        source_type="computational",
        source_name="model",
        summary="structure provenance",
        design_id=root.id,
        file_paths=[str(structure_file.relative_to(project.root_dir))],
    )
    project.archive.add_evidence(entry)
    project.save()

    monkeypatch.setattr(api, "PROJECTS_ROOT", projects_root)
    client = TestClient(api.app)
    response = client.delete(f"/api/projects/demo/evidence/{entry.id}")

    assert response.status_code == 200
    assert structure_file.is_file()
