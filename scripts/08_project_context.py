from human_protein_design.archive import DesignProject, export_project_context
from human_protein_design.cli import choose_project


def main() -> None:
    """Export one portable Markdown snapshot of a selected HGD project."""
    project_dir = choose_project()
    project = DesignProject.load(name=project_dir.name, root_dir=project_dir)

    output = export_project_context(
        archive=project.archive,
        output_path=project.root_dir / "PROJECT_CONTEXT.md",
        project_name=project.name,
    )

    print("\nProject context exported.")
    print(f"Output: {output}")
    print("This Markdown file contains a readable scientific summary plus the complete archive JSON for LLM use.")


if __name__ == "__main__":
    main()
