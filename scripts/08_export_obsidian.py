from pathlib import Path

from human_protein_design.archive import (
    DesignProject,
    export_obsidian_vault,
)


PROJECT_DIR = Path(
    "data/projects/gb1_design"
)

OBSIDIAN_DIR = (
    PROJECT_DIR
    / "obsidian"
)


def main() -> None:
    """Export project archive to Obsidian Markdown."""

    project = DesignProject.load(
        name="GB1 Human-Guided Design",
        root_dir=PROJECT_DIR,
    )

    export_obsidian_vault(
        archive=project.archive,
        output_dir=OBSIDIAN_DIR,
    )

    print(
        "\nObsidian export complete."
    )

    print(
        f"Output: {OBSIDIAN_DIR}"
    )

    print(
        f"Designs exported: "
        f"{len(project.archive.designs)}"
    )


if __name__ == "__main__":
    main()