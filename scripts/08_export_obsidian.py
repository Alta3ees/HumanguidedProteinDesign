from human_protein_design.archive import (
    DesignProject,
    export_obsidian_vault,
)
from human_protein_design.cli import choose_project


def main() -> None:
    """Export a selected project archive to Obsidian Markdown."""
    project_dir = choose_project()
    project = DesignProject.load(name=project_dir.name, root_dir=project_dir)
    obsidian_dir = project.root_dir / "obsidian"

    export_obsidian_vault(
        archive=project.archive,
        output_dir=obsidian_dir,
    )

    print("\nObsidian export complete.")
    print(f"Output: {obsidian_dir}")
    print(f"Designs exported: {len(project.archive.designs)}")


if __name__ == "__main__":
    main()
