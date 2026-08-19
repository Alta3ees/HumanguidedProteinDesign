import json

from fastapi.testclient import TestClient

from human_protein_design.archive import Design, DesignProject, EvidenceEntry, ProjectObjective
from human_protein_design.web import api
from human_protein_design.web.file_preview import preview_file


def make_project(projects_root):
    project = DesignProject(name="demo", root_dir=projects_root / "demo")
    objective = ProjectObjective(description="Test web scientific features")
    project.archive.add_objective(objective)
    design = Design(
        name="WT",
        sequence="ACDEFG",
        origin="natural_sequence",
        objective_id=objective.id,
    )
    project.archive.add_design(design)
    project.save()
    return project, design


def test_common_scientific_file_previews(tmp_path):
    csv_path = tmp_path / "scores.csv"
    csv_path.write_text("mutation,delta_score\nA1V,-1.2\nA1W,2.3\n", encoding="utf-8")
    csv_preview = preview_file(csv_path)
    assert csv_preview["kind"] == "table"
    assert csv_preview["headers"] == ["mutation", "delta_score"]
    assert csv_preview["rows"][0] == ["A1V", "-1.2"]

    fasta_path = tmp_path / "designs.fasta"
    fasta_path.write_text(">WT\nACDEFG\n>candidate\nACDEWG\n", encoding="utf-8")
    fasta_preview = preview_file(fasta_path)
    assert fasta_preview["kind"] == "fasta"
    assert [item["length"] for item in fasta_preview["records"]] == [6, 6]

    json_path = tmp_path / "pae.json"
    json_path.write_text(json.dumps({"pae": [[0, 1], [1, 0]]}), encoding="utf-8")
    json_preview = preview_file(json_path)
    assert json_preview["kind"] == "json"
    assert json_preview["data"]["pae"][0][1] == 1

    score_path = tmp_path / "rosetta.sc"
    score_path.write_text(
        "SCORE: total_score fa_atr description\n"
        "SCORE: -10.0 -20.0 model_1\n",
        encoding="utf-8",
    )
    score_preview = preview_file(score_path)
    assert score_preview["kind"] == "rosetta_score"
    assert score_preview["headers"][0] == "total_score"
    assert score_preview["rows"][0][-1] == "model_1"


def test_preview_api_stays_project_local(tmp_path, monkeypatch):
    projects_root = tmp_path / "projects"
    project, _ = make_project(projects_root)
    table = project.root_dir / "experiment.tsv"
    table.write_text("x\ty\n1\t2\n", encoding="utf-8")

    monkeypatch.setattr(api, "PROJECTS_ROOT", projects_root)
    client = TestClient(api.app)
    response = client.get("/api/projects/demo/preview/experiment.tsv")
    assert response.status_code == 200
    assert response.json()["kind"] == "table"
    assert response.json()["rows"] == [["1", "2"]]


def test_project_summary_and_obsidian_exports_are_web_actions(tmp_path, monkeypatch):
    projects_root = tmp_path / "projects"
    project, _ = make_project(projects_root)
    monkeypatch.setattr(api, "PROJECTS_ROOT", projects_root)
    client = TestClient(api.app)

    summary = client.post("/api/projects/demo/export/summary")
    assert summary.status_code == 200
    summary_path = project.root_dir / summary.json()["file_path"]
    assert summary_path.is_file()

    obsidian = client.post("/api/projects/demo/export/obsidian")
    assert obsidian.status_code == 200
    assert obsidian.json()["files"]
    assert (project.root_dir / obsidian.json()["output_dir"]).is_dir()


def test_position_scan_route_returns_ranking_without_embedding_science_in_route(tmp_path, monkeypatch):
    projects_root = tmp_path / "projects"
    project, design = make_project(projects_root)
    evidence = EvidenceEntry(
        source_type="computational",
        source_name="PyRosetta saturation scan",
        summary="scan",
        design_id=design.id,
    )

    def fake_scan(project_arg, *, design_id, position, radius):
        assert project_arg.root_dir == project.root_dir
        assert design_id == design.id
        assert position == 3
        assert radius == 8.0
        return (
            evidence,
            [{"mutation": "D3W", "position": 3, "wt_aa": "D", "mutant_aa": "W", "total_score": -4.0, "delta_score": -1.2}],
            [2, 3, 4],
            "evidence/mutation_scans/D3_scan.csv",
        )

    monkeypatch.setattr(api, "PROJECTS_ROOT", projects_root)
    monkeypatch.setattr(api, "run_position_scan", fake_scan)
    client = TestClient(api.app)
    response = client.post(
        f"/api/projects/demo/designs/{design.id}/position-scan",
        json={"position": 3, "radius": 8.0},
    )
    assert response.status_code == 200
    assert response.json()["results"][0]["mutation"] == "D3W"


def test_point_mutation_route_returns_archived_candidate(tmp_path, monkeypatch):
    projects_root = tmp_path / "projects"
    project, design = make_project(projects_root)

    def fake_evaluate(project_arg, **kwargs):
        assert project_arg.root_dir == project.root_dir
        assert kwargs["design_id"] == design.id
        assert kwargs["mutant_aa"] == "W"
        return "candidate-123", {
            "mutation": "D3W",
            "previous_score": -3.0,
            "mutant_score": -4.0,
            "delta_score": -1.0,
        }

    monkeypatch.setattr(api, "PROJECTS_ROOT", projects_root)
    monkeypatch.setattr(api, "evaluate_point_mutation", fake_evaluate)
    client = TestClient(api.app)
    response = client.post(
        f"/api/projects/demo/designs/{design.id}/evaluate-mutation",
        json={"position": 3, "mutant_aa": "W", "hypothesis": "pack better", "objective": "stability"},
    )
    assert response.status_code == 200
    assert response.json()["candidate_design_id"] == "candidate-123"
    assert response.json()["evaluation"]["delta_score"] == -1.0
