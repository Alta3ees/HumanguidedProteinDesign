"""Local FastAPI surface for the v0.4 research workspace.

The API is intentionally local-first. Project data remains on the scientist's
machine under ``data/projects`` (or ``HGD_PROJECTS_ROOT``). The frontend never
writes archive JSON directly; imports go through the validated Python archive.
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from human_protein_design.archive import DesignProject, EvidenceEntry


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROJECTS_ROOT = REPOSITORY_ROOT / "data" / "projects"
PROJECTS_ROOT = Path(os.environ.get("HGD_PROJECTS_ROOT", DEFAULT_PROJECTS_ROOT)).expanduser().resolve()
ALLOWED_EVIDENCE_TYPES = {"computational", "experimental", "literature", "note"}

app = FastAPI(
    title="Human-Guided Protein Design API",
    version="0.4.0-dev",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _project_dir(slug: str) -> Path:
    if not slug or slug in {".", ".."} or any(char in slug for char in "/\\"):
        raise HTTPException(status_code=400, detail="Invalid project slug.")
    path = PROJECTS_ROOT / slug
    if not path.is_dir():
        raise HTTPException(status_code=404, detail="Project not found.")
    if not (path / "design_archive.json").is_file():
        raise HTTPException(status_code=404, detail="Project archive not found.")
    return path


def _safe_filename(filename: str | None) -> str:
    """Return a conservative basename for a locally uploaded file."""
    raw = Path(filename or "evidence_file").name
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("._")
    return safe or "evidence_file"


def _unique_path(directory: Path, filename: str) -> Path:
    candidate = directory / filename
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    counter = 2
    while True:
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
            for child in sorted(
                archive.get_children(design_id),
                key=lambda item: item.created_at,
            )
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


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "projects_root": str(PROJECTS_ROOT)}


@app.get("/api/projects")
def list_projects() -> list[dict[str, Any]]:
    if not PROJECTS_ROOT.exists():
        return []

    projects: list[dict[str, Any]] = []
    for path in sorted(PROJECTS_ROOT.iterdir(), key=lambda item: item.name.lower()):
        archive_path = path / "design_archive.json"
        if not path.is_dir() or not archive_path.is_file():
            continue
        try:
            project = DesignProject.load(name=path.name, root_dir=path)
        except (ValueError, OSError):
            continue
        projects.append(
            {
                "slug": path.name,
                "name": project.name,
                "schema_version": project.archive.SCHEMA_VERSION,
                "design_count": len(project.archive.designs),
                "structure_count": len(project.archive.structures),
                "evidence_count": len(project.archive.evidence),
            }
        )
    return projects


@app.get("/api/projects/{slug}")
def get_project(slug: str) -> dict[str, Any]:
    path = _project_dir(slug)
    project = DesignProject.load(name=path.name, root_dir=path)
    return _project_payload(project, slug)


@app.get("/api/projects/{slug}/files/{relative_path:path}")
def open_project_file(slug: str, relative_path: str) -> FileResponse:
    """Serve one imported evidence file from the local project only.

    The route is deliberately restricted to the project's ``evidence``
    directory so the browser cannot request arbitrary files from the machine.
    """
    project_path = _project_dir(slug)
    evidence_root = (project_path / "evidence").resolve()
    requested = Path(relative_path)

    if requested.is_absolute():
        raise HTTPException(status_code=400, detail="Invalid file path.")

    candidate = (project_path / requested).resolve()
    try:
        candidate.relative_to(evidence_root)
    except ValueError as error:
        raise HTTPException(status_code=403, detail="File is outside project evidence storage.") from error

    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Evidence file not found.")

    return FileResponse(candidate)


@app.post("/api/projects/{slug}/designs/{design_id}/evidence")
def import_design_evidence(
    slug: str,
    design_id: str,
    source_type: str = Form(...),
    source_name: str = Form(...),
    summary: str = Form(...),
    notes: str = Form(""),
    files: list[UploadFile] = File(...),
) -> dict[str, Any]:
    """Import local files and attach them as evidence to one design.

    Uploaded bytes never leave the local FastAPI process. They are copied into
    the project's ``evidence`` directory and referenced by project-relative
    paths in the canonical archive.
    """
    path = _project_dir(slug)
    project = DesignProject.load(name=path.name, root_dir=path)

    if design_id not in project.archive.designs:
        raise HTTPException(status_code=404, detail="Design not found.")

    source_type = source_type.strip().lower()
    if source_type not in ALLOWED_EVIDENCE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid evidence type.")

    source_name = source_name.strip()
    summary = summary.strip()
    if not source_name:
        raise HTTPException(status_code=400, detail="Source name is required.")
    if not summary:
        raise HTTPException(status_code=400, detail="Summary is required.")
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required.")

    import_dir = project.evidence_dir / f"import_{uuid4().hex[:12]}"
    import_dir.mkdir(parents=True, exist_ok=False)
    stored_paths: list[str] = []

    try:
        for uploaded in files:
            filename = _safe_filename(uploaded.filename)
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

    evidence = EvidenceEntry(
        source_type=source_type,
        source_name=source_name,
        summary=summary,
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
