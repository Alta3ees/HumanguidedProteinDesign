"""Utilities for attaching external scientific evidence to designs."""

from __future__ import annotations

import shutil

from pathlib import Path
from typing import Any

from human_protein_design.archive.models import (
    EvidenceEntry,
)
from human_protein_design.archive.store import (
    DesignArchive,
)


def _safe_name(
    text: str,
) -> str:
    """Return a filesystem-safe name."""

    return (
        text.strip()
        .replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
    )


def copy_evidence_files(
    files: list[str | Path],
    project_root: str | Path,
    source_type: str,
    source_name: str,
) -> list[str]:
    """
    Copy evidence files into the project.

    Returned paths are relative to project_root.
    """

    project_root = Path(
        project_root
    )

    source_dir = (
        project_root
        / "evidence"
        / _safe_name(source_type)
        / _safe_name(source_name)
    )

    source_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    stored_paths: list[str] = []

    for file in files:

        source_path = Path(
            file
        ).expanduser()

        if not source_path.exists():
            raise FileNotFoundError(
                f"Evidence file does not exist: "
                f"{source_path}"
            )

        if not source_path.is_file():
            raise ValueError(
                f"Evidence path is not a file: "
                f"{source_path}"
            )

        destination = (
            source_dir
            / source_path.name
        )

        # --------------------------------
        # Avoid overwriting existing files
        # --------------------------------

        if destination.exists():

            stem = destination.stem
            suffix = destination.suffix

            counter = 2

            while destination.exists():

                destination = (
                    source_dir
                    / f"{stem}_{counter}{suffix}"
                )

                counter += 1

        shutil.copy2(
            source_path,
            destination,
        )

        relative_path = (
            destination.relative_to(
                project_root
            )
        )

        stored_paths.append(
            str(relative_path)
        )

    return stored_paths


def add_external_evidence(
    archive: DesignArchive,
    design_id: str,
    source_type: str,
    source_name: str,
    summary: str,
    data: dict[str, Any] | None = None,
    files: list[str | Path] | None = None,
    references: list[str] | None = None,
    notes: str | None = None,
    project_root: str | Path | None = None,
    copy_files: bool = True,
) -> EvidenceEntry:
    """
    Attach scientific evidence to a design.

    If project_root is supplied and copy_files is True,
    attached files are copied into the project evidence
    directory and stored using project-relative paths.
    """

    if design_id not in archive.designs:
        raise ValueError(
            f"Unknown design: {design_id}"
        )

    file_paths: list[str] = []

    if files:

        if copy_files:

            if project_root is None:
                raise ValueError(
                    "project_root is required when "
                    "copy_files=True."
                )

            file_paths = copy_evidence_files(
                files=files,
                project_root=project_root,
                source_type=source_type,
                source_name=source_name,
            )

        else:

            file_paths = [
                str(
                    Path(file).expanduser()
                )
                for file in files
            ]

    evidence = EvidenceEntry(
        source_type=source_type,
        source_name=source_name,
        summary=summary,
        design_id=design_id,
        data=data or {},
        file_paths=file_paths,
        references=references or [],
        notes=notes,
    )

    archive.add_evidence(
        evidence
    )

    return evidence