"""Local FastAPI surface for the v0.4 research workspace."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from human_protein_design.archive import DesignProject, EvidenceEntry
from human_protein_design.web.actions import (
    attach_structure_file,
    create_derived_sequence_design,
    create_project,
    delete_evidence,
    register_design,
    safe_filename,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROJECTS_ROOT = REPOSITORY_ROOT / "data" / "projects"
PROJECTS_ROOT = Path(os.environ.get("HGD_PROJECTS_ROOT", DEFAULT_PROJECTS_ROOT)).expanduser().resolve()
ALLOWED_EVIDENCE_TYPES = {"computational", "experimental", "literature", "note"}

app = FastAPI(title="Human-Guided Protein Design API", version="0.4.0-dev")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


class NewProjectRequest(BaseModel):
    name: str
    objective: str
    sequence: str | None = None
    design_name: str | None = None
    target_name: str | None = None
    target_sequence: str | None = None


class DerivedSequenceRequest(BaseModel):
    sequence: str
    name: str | None = None
    hypothesis: str | None = None


class RegisterDesignRequest(BaseModel):
    name: str
    origin: str
    sequence: str | None = None
    parent_design_id: str | None = None
    hypothesis: str | None = None
    source_tool: str | None = None


class LaunchPyMOLRequest(BaseModel):
    relative_path: str


def _project_dir(slug: str) -> Path:
    if not slug or slug in {".", ".."} or any(char in slug for char in "/\\"):
        raise HTTPException(status_code=400, detail="Invalid project slug.")
    path = PROJECTS_ROOT / slug
    if not path.is_dir():
        raise HTTPException(status_code=404, detail="Project not found.")
    if not (path / "design_archive.json").is_file():
        raise HTTPException(status_code=404, detail="Project archive not found.")
    return path


def _project_file(slug: str, relative_path: str) -> Path:
    """Resolve one file while keeping access inside the selected project."""
    project_path = _project_dir(slug).resolve()
    requested = Path(relative_path)
    if requested.is_absolute():
        raise HTTPException(status_code=400, detail="Expected a project-relative file path.")
    candidate = (project_path / requested).resolve()
    try:
        candidate.relative_to(project_path)
    except ValueError as error:
        raise HTTPException(status_code=403, detail="File is outside the selected project directory.") from error
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Project file not found.")
    return candidate


def _load_project(slug: str) -> DesignProject:
    path = _project_dir(slug)
    return DesignProject.load(name=path.name, root_dir=path)


def _safe_filename(filename: str | None) -> str:
    raw = Path(filename or "evidence_file").name
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("._")
    return safe or "evidence_file"


def _unique_path(directory: Path, filename: str) -> Path:
    candidate = directory / filename
    if not candidate.exists():
        return candidate
    stem, suffix, counter = candidate.stem, candidate.suffix, 2
    while candidate.exists():
        candidate = directory / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _design_payload(project: DesignProject, design_id: str) -> dict[str, Any]:
    archive = project.archive
    design = archive.get_design(design_id)
    structures = archive.get_design_structures(design_id)
    evidence = archive.get_design_evidence(design_id)
    decisions = archive.get_design_decisions(design_id)
    return {
        **design.to_dict(),
        "label": archive.get_design_label(design_id),
        "lineage_label": archive.get_lineage_label(design_id),
        "decision": decisions[-1].to_dict() if decisions else None,
        "structures": [item.to_dict() for item in structures],
        "evidence": [item.to_dict() for item in evidence],
        "evidence_counts": archive.get_design_evidence_counts(design_id),
        "children": [
            _design_payload(project, child.id)
            for child in sorted(archive.get_children(design_id), key=lambda item: item.created_at)
        ],
    }


def _project_payload(project: DesignProject, slug: str) -> dict[str, Any]:
    archive = project.archive
    roots = sorted(archive.get_root_designs(), key=lambda item: item.created_at)
    return {
        "slug": slug,
        "name": project.name,
        "schema_version": archive.SCHEMA_VERSION,
        "counts": {
            "designs": len(archive.designs),
            "structures": len(archive.structures),
            "decisions": len(archive.decisions),
            "evidence": len(archive.evidence),
            "objectives": len(archive.objectives),
            "targets": len(archive.targets),
        },
        "objectives": [item.to_dict() for item in archive.objectives.values()],
        "targets": [item.to_dict() for item in archive.targets.values()],
        "design_tree": [_design_payload(project, root.id) for root in roots],
    }


def _project_list_item(project: DesignProject, slug: str) -> dict[str, Any]:
    return {
        "slug": slug,
        "name": project.name,
        "schema_version": project.archive.SCHEMA_VERSION,
        "design_count": len(project.archive.designs),
        "structure_count": len(project.archive.structures),
        "evidence_count": len(project.archive.evidence),
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "projects_root": str(PROJECTS_ROOT)}


@app.get("/api/projects")
def list_projects() -> list[dict[str, Any]]:
    if not PROJECTS_ROOT.exists():
        return []
    projects: list[dict[str, Any]] = []
    for path in sorted(PROJECTS_ROOT.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_dir() or not (path / "design_archive.json").is_file():
            continue
        try:
            project = DesignProject.load(name=path.name, root_dir=path)
        except (ValueError, OSError):
            continue
        projects.append(_project_list_item(project, path.name))
    return projects


@app.post("/api/projects")
def create_project_endpoint(request: NewProjectRequest) -> dict[str, Any]:
    try:
        project = create_project(
            projects_root=PROJECTS_ROOT,
            name=request.name,
            objective=request.objective,
            sequence=request.sequence,
            design_name=request.design_name,
            target_name=request.target_name,
            target_sequence=request.target_sequence,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {
        "list_item": _project_list_item(project, project.root_dir.name),
        "project": _project_payload(project, project.root_dir.name),
    }


@app.get("/api/projects/{slug}")
def get_project(slug: str) -> dict[str, Any]:
    return _project_payload(_load_project(slug), slug)


@app.post("/api/projects/{slug}/designs/{design_id}/derive-sequence")
def derive_sequence(slug: str, design_id: str, request: DerivedSequenceRequest) -> dict[str, Any]:
    project = _load_project(slug)
    try:
        design = create_derived_sequence_design(
            project,
            parent_design_id=design_id,
            sequence=request.sequence,
            name=request.name,
            hypothesis=request.hypothesis,
        )
    except (ValueError, KeyError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"design_id": design.id, "project": _project_payload(project, slug)}


@app.post("/api/projects/{slug}/designs")
def register_design_endpoint(slug: str, request: RegisterDesignRequest) -> dict[str, Any]:
    project = _load_project(slug)
    try:
        design = register_design(
            project,
            name=request.name,
            origin=request.origin,
            sequence=request.sequence,
            parent_design_id=request.parent_design_id,
            hypothesis=request.hypothesis,
            source_tool=request.source_tool,
        )
    except (ValueError, KeyError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"design_id": design.id, "project": _project_payload(project, slug)}


@app.post("/api/projects/{slug}/designs/{design_id}/structures")
def attach_structure_endpoint(
    slug: str,
    design_id: str,
    source: str = Form("user"),
    method: str = Form(""),
    mean_plddt: float | None = Form(None),
    ptm: float | None = Form(None),
    iptm: float | None = Form(None),
    notes: str = Form(""),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    project = _load_project(slug)
    filename = safe_filename(file.filename, "structure.pdb")
    try:
        with tempfile.TemporaryDirectory(prefix="hgd_structure_", dir=project.root_dir) as temp_dir:
            temp_path = Path(temp_dir) / filename
            with temp_path.open("wb") as handle:
                shutil.copyfileobj(file.file, handle)
            structure = attach_structure_file(
                project,
                design_id=design_id,
                source_path=temp_path,
                source=source.strip().lower(),
                method=method,
                mean_plddt=mean_plddt,
                ptm=ptm,
                iptm=iptm,
                notes=notes,
            )
    except (ValueError, KeyError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    finally:
        file.file.close()
    return {"structure": structure.to_dict(), "project": _project_payload(project, slug)}


@app.get("/api/projects/{slug}/files/{relative_path:path}")
def open_project_file(slug: str, relative_path: str) -> FileResponse:
    """Serve any file stored inside the selected local HGD project directory."""
    return FileResponse(_project_file(slug, relative_path))


@app.post("/api/projects/{slug}/launch-pymol")
def launch_pymol(slug: str, request: LaunchPyMOLRequest) -> dict[str, str]:
    """Launch local PyMOL and report immediate startup failures instead of guessing."""
    structure_path = _project_file(slug, request.relative_path)
    suffix = structure_path.suffix.lower()
    if suffix not in {".pdb", ".ent", ".cif", ".mmcif", ".pqr"}:
        raise HTTPException(status_code=400, detail="PyMOL launch is limited to molecular structure files.")

    pymol_executable = shutil.which("pymol")
    if pymol_executable is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "PyMOL was not found in the backend environment. "
                "Install/activate the environment from environment.yml, then restart HGD."
            ),
        )

    project_path = _project_dir(slug).resolve()
    runtime_dir = project_path / ".hgd"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    log_path = runtime_dir / "pymol-launch.log"

    try:
        with log_path.open("w", encoding="utf-8") as log_handle:
            process = subprocess.Popen(
                [pymol_executable, str(structure_path)],
                cwd=str(structure_path.parent),
                start_new_session=True,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
            )
        time.sleep(1.0)
    except OSError as error:
        raise HTTPException(status_code=500, detail=f"Could not launch PyMOL: {error}") from error

    return_code = process.poll()
    if return_code not in {None, 0}:
        try:
            diagnostic = log_path.read_text(encoding="utf-8").strip()
        except OSError:
            diagnostic = ""
        if diagnostic:
            diagnostic = diagnostic[-3000:]
        else:
            diagnostic = f"PyMOL exited immediately with code {return_code}."
        raise HTTPException(
            status_code=500,
            detail=f"PyMOL failed to start. {diagnostic}",
        )

    status = "running" if return_code is None else "launcher_exited"
    return {
        "status": status,
        "file": request.relative_path,
        "log": str(log_path.relative_to(project_path)),
    }


@app.post("/api/projects/{slug}/designs/{design_id}/evidence")
def import_design_evidence(
    slug: str,
    design_id: str,
    source_type: str = Form("experimental"),
    source_name: str = Form(""),
    summary: str = Form(""),
    notes: str = Form(""),
    files: list[UploadFile] = File(...),
) -> dict[str, Any]:
    project = _load_project(slug)
    if design_id not in project.archive.designs:
        raise HTTPException(status_code=404, detail="Design not found.")

    source_type = source_type.strip().lower()
    if source_type not in ALLOWED_EVIDENCE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid evidence type.")
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required.")

    import_dir = project.evidence_dir / f"import_{uuid4().hex[:12]}"
    import_dir.mkdir(parents=True, exist_ok=False)
    stored_paths: list[str] = []
    original_names: list[str] = []
    try:
        for uploaded in files:
            filename = _safe_filename(uploaded.filename)
            original_names.append(filename)
            destination = _unique_path(import_dir, filename)
            with destination.open("wb") as handle:
                shutil.copyfileobj(uploaded.file, handle)
            stored_paths.append(str(destination.relative_to(project.root_dir)))
    except Exception:
        shutil.rmtree(import_dir, ignore_errors=True)
        raise
    finally:
        for uploaded in files:
            uploaded.file.close()

    first_name = original_names[0] if original_names else "local evidence"
    resolved_source_name = source_name.strip() or Path(first_name).stem or source_type.title()
    resolved_summary = summary.strip() or (
        f"Imported local file: {first_name}"
        if len(original_names) == 1
        else f"Imported {len(original_names)} local files."
    )
    evidence = EvidenceEntry(
        source_type=source_type,
        source_name=resolved_source_name,
        summary=resolved_summary,
        notes=notes.strip() or None,
        design_id=design_id,
        file_paths=stored_paths,
        data={"import_method": "local_web_upload"},
    )
    project.archive.add_evidence(evidence)
    project.save()
    return {
        "evidence": evidence.to_dict(),
        "stored_files": stored_paths,
        "project": _project_payload(project, slug),
    }


@app.delete("/api/projects/{slug}/evidence/{evidence_id}")
def delete_evidence_endpoint(slug: str, evidence_id: str) -> dict[str, Any]:
    project = _load_project(slug)
    try:
        deleted_files = delete_evidence(project, evidence_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"deleted_files": deleted_files, "project": _project_payload(project, slug)}
