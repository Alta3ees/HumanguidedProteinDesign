"""Persistent protein-design project."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from human_protein_design.archive.store import DesignArchive


@dataclass
class DesignProject:
    """A persistent protein-design project."""

    name: str
    root_dir: str | Path
    archive: DesignArchive = field(default_factory=DesignArchive)

    def __post_init__(self) -> None:
        self.root_dir = Path(self.root_dir)
        for directory in (
            self.structures_dir,
            self.evidence_dir,
            self.sessions_dir,
            self.inputs_dir,
            self.outputs_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    @property
    def archive_path(self) -> Path:
        return self.root_dir / "design_archive.json"

    @property
    def structures_dir(self) -> Path:
        return self.root_dir / "structures"

    @property
    def evidence_dir(self) -> Path:
        return self.root_dir / "evidence"

    @property
    def sessions_dir(self) -> Path:
        return self.root_dir / "sessions"

    @property
    def inputs_dir(self) -> Path:
        return self.root_dir / "inputs"

    @property
    def outputs_dir(self) -> Path:
        return self.root_dir / "outputs"

    def save(self) -> None:
        """Save archive and regenerate the human-readable summary."""
        from human_protein_design.archive.summary import export_project_summary
        self.archive.save(self.archive_path)
        export_project_summary(
            archive=self.archive,
            output_path=self.root_dir / "PROJECT_SUMMARY.md",
            project_name=self.name,
        )

    @classmethod
    def load(cls, name: str, root_dir: str | Path) -> "DesignProject":
        """Load an existing project, automatically reading v0.3 archives."""
        root_dir = Path(root_dir)
        project = cls(name=name, root_dir=root_dir)
        if project.archive_path.exists():
            project.archive = DesignArchive.load(project.archive_path)
        return project
