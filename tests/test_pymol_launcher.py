from fastapi.testclient import TestClient

from human_protein_design.archive import Design, DesignProject, ProjectObjective
from human_protein_design.web import api


def make_project(projects_root):
    project = DesignProject(name="demo", root_dir=projects_root / "demo")
    objective = ProjectObjective(description="Inspect a local structure")
    project.archive.add_objective(objective)
    design = Design(name="WT", sequence="ACDEFG", origin="natural_sequence", objective_id=objective.id)
    project.archive.add_design(design)
    project.structures_dir.mkdir(parents=True, exist_ok=True)
    structure = project.structures_dir / "model.pdb"
    structure.write_text("ATOM      1  CA  ALA A   1       0.000   0.000   0.000\n", encoding="utf-8")
    project.save()
    return project, structure


def test_launch_pymol_uses_project_structure_and_environment_executable(tmp_path, monkeypatch):
    projects_root = tmp_path / "projects"
    project, structure = make_project(projects_root)
    monkeypatch.setattr(api, "PROJECTS_ROOT", projects_root)
    monkeypatch.setattr(api.shutil, "which", lambda name: "/fake/env/bin/pymol" if name == "pymol" else None)
    monkeypatch.setattr(api.time, "sleep", lambda _seconds: None)

    launched = {}

    class DummyProcess:
        def poll(self):
            return None

    def fake_popen(command, **kwargs):
        launched["command"] = command
        launched["kwargs"] = kwargs
        return DummyProcess()

    monkeypatch.setattr(api.subprocess, "Popen", fake_popen)
    client = TestClient(api.app)
    response = client.post(
        "/api/projects/demo/launch-pymol",
        json={"relative_path": "structures/model.pdb"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "running"
    assert launched["command"] == ["/fake/env/bin/pymol", str(structure.resolve())]
    assert launched["kwargs"]["cwd"] == str(project.structures_dir.resolve())
    assert response.json()["log"] == ".hgd/pymol-launch.log"


def test_launch_pymol_reports_immediate_crash(tmp_path, monkeypatch):
    projects_root = tmp_path / "projects"
    make_project(projects_root)
    monkeypatch.setattr(api, "PROJECTS_ROOT", projects_root)
    monkeypatch.setattr(api.shutil, "which", lambda _name: "/fake/env/bin/pymol")
    monkeypatch.setattr(api.time, "sleep", lambda _seconds: None)

    class CrashedProcess:
        def poll(self):
            return 1

    def fake_popen(_command, **kwargs):
        kwargs["stdout"].write("Qt platform plugin could not be initialized\n")
        kwargs["stdout"].flush()
        return CrashedProcess()

    monkeypatch.setattr(api.subprocess, "Popen", fake_popen)
    client = TestClient(api.app)
    response = client.post(
        "/api/projects/demo/launch-pymol",
        json={"relative_path": "structures/model.pdb"},
    )

    assert response.status_code == 500
    assert "Qt platform plugin" in response.json()["detail"]


def test_launch_pymol_reports_missing_environment_install(tmp_path, monkeypatch):
    projects_root = tmp_path / "projects"
    make_project(projects_root)
    monkeypatch.setattr(api, "PROJECTS_ROOT", projects_root)
    monkeypatch.setattr(api.shutil, "which", lambda _name: None)
    client = TestClient(api.app)

    response = client.post(
        "/api/projects/demo/launch-pymol",
        json={"relative_path": "structures/model.pdb"},
    )

    assert response.status_code == 503
    assert "PyMOL was not found" in response.json()["detail"]


def test_launch_pymol_cannot_escape_project(tmp_path, monkeypatch):
    projects_root = tmp_path / "projects"
    make_project(projects_root)
    outside = tmp_path / "outside.pdb"
    outside.write_text("ATOM\n", encoding="utf-8")
    monkeypatch.setattr(api, "PROJECTS_ROOT", projects_root)
    client = TestClient(api.app)

    response = client.post(
        "/api/projects/demo/launch-pymol",
        json={"relative_path": "../../outside.pdb"},
    )

    assert response.status_code == 403
