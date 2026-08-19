from fastapi.testclient import TestClient

from human_protein_design.archive import Design, DesignProject, EvidenceEntry, ProjectObjective, StructureModel
from human_protein_design.web import api


def make_demo_project(projects_root):
    project_dir = projects_root / "demo"
    project = DesignProject(name="demo", root_dir=project_dir)
    objective = ProjectObjective(description="Explore a candidate protein")
    project.archive.add_objective(objective)
    root = Design(name="WT", sequence="ACDEFG", origin="natural_sequence", objective_id=objective.id)
    project.archive.add_design(root)
    return project, root


def test_project_api_exposes_design_tree(tmp_path, monkeypatch):
    projects_root = tmp_path / "projects"
    project, root = make_demo_project(projects_root)
    child = Design(
        name="WT -> F6W",
        sequence="ACDEWG",
        origin="point_mutation",
        parent_design_id=root.id,
        objective_id=next(iter(project.archive.objectives)),
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


def test_local_file_upload_is_archived_as_evidence(tmp_path, monkeypatch):
    projects_root = tmp_path / "projects"
    project, root = make_demo_project(projects_root)
    project.save()

    monkeypatch.setattr(api, "PROJECTS_ROOT", projects_root)
    client = TestClient(api.app)

    response = client.post(
        f"/api/projects/demo/designs/{root.id}/evidence",
        data={
            "source_type": "experimental",
            "source_name": "NMR",
            "summary": "Imported local spectrum for inspection.",
            "notes": "Raw data retained unchanged.",
        },
        files=[
            ("files", ("spectrum.ucsf", b"local-nmr-bytes", "application/octet-stream")),
            ("files", ("notes.txt", b"acquisition notes", "text/plain")),
        ],
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["stored_files"]) == 2
    assert payload["project"]["counts"]["evidence"] == 1

    reloaded = DesignProject.load(name="demo", root_dir=projects_root / "demo")
    entries = reloaded.archive.get_design_evidence(root.id)
    assert len(entries) == 1
    assert entries[0].source_type == "experimental"
    assert entries[0].source_name == "NMR"
    assert len(entries[0].file_paths) == 2
    for relative_path in entries[0].file_paths:
        assert (project.root_dir / relative_path).is_file()


def test_quick_attach_derives_metadata_and_file_can_be_opened(tmp_path, monkeypatch):
    projects_root = tmp_path / "projects"
    project, root = make_demo_project(projects_root)
    project.save()

    monkeypatch.setattr(api, "PROJECTS_ROOT", projects_root)
    client = TestClient(api.app)

    upload = client.post(
        f"/api/projects/demo/designs/{root.id}/evidence",
        data={"source_type": "literature"},
        files={"files": ("paper.pdf", b"local-pdf-bytes", "application/pdf")},
    )
    assert upload.status_code == 200
    payload = upload.json()
    evidence = payload["evidence"]
    assert evidence["source_name"] == "paper"
    assert evidence["summary"] == "Imported local file: paper.pdf"

    stored_path = payload["stored_files"][0]
    opened = client.get(f"/api/projects/demo/files/{stored_path}")
    assert opened.status_code == 200
    assert opened.content == b"local-pdf-bytes"


def test_local_file_route_cannot_escape_evidence_directory(tmp_path, monkeypatch):
    projects_root = tmp_path / "projects"
    project, _ = make_demo_project(projects_root)
    project.save()
    secret = project.root_dir / "secret.txt"
    secret.write_text("private", encoding="utf-8")

    monkeypatch.setattr(api, "PROJECTS_ROOT", projects_root)
    client = TestClient(api.app)
    response = client.get("/api/projects/demo/files/secret.txt")
    assert response.status_code == 403


def test_project_api_rejects_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "PROJECTS_ROOT", tmp_path)
    client = TestClient(api.app)
    response = client.get("/api/projects/..%5Csecret")
    assert response.status_code == 400
