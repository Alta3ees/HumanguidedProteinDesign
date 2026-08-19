"""Read-only FastAPI surface for the v0.4 research workspace."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from human_protein_design.archive import DesignProject


PROJECTS_ROOT = Path(os.environ.get("HGD_PROJECTS_ROOT", "data/projects"))

app = FastAPI(
    title="Human-Guided Protein Design API",
    version="0.4.0-dev",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET"],
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
    return {"status": "ok"}


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
