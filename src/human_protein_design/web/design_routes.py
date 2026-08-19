"""Additional design routes registered by the HGD workspace launcher."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from human_protein_design.web.design_delete import delete_leaf_design

router = APIRouter()


@router.delete("/api/projects/{slug}/designs/{design_id}")
def delete_design_endpoint(slug: str, design_id: str) -> dict[str, Any]:
    # Imported lazily to avoid a circular import while api.py is defining app.
    from human_protein_design.web.api import _load_project, _project_payload

    project = _load_project(slug)
    try:
        result = delete_leaf_design(project, design_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    return {**result, "project": _project_payload(project, slug)}
