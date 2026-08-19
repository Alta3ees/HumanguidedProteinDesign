from human_protein_design.archive import Design, DesignProject


def test_project_save_persists_archive_without_generating_context(tmp_path):
    project = DesignProject(name="demo", root_dir=tmp_path / "demo")
    project.archive.add_design(
        Design(
            name="WT",
            sequence="ACDEFG",
            origin="natural_sequence",
        )
    )

    project.save()

    assert project.archive_path.is_file()
    assert not (project.root_dir / "PROJECT_CONTEXT.md").exists()
    assert not (project.root_dir / "PROJECT_SUMMARY.md").exists()


def test_project_save_can_be_loaded_without_markdown_side_effects(tmp_path):
    project = DesignProject(name="demo", root_dir=tmp_path / "demo")
    design = Design(
        name="WT",
        sequence="ACDEFG",
        origin="natural_sequence",
    )
    project.archive.add_design(design)
    project.save()

    loaded = DesignProject.load(name="demo", root_dir=project.root_dir)

    assert loaded.archive.get_design(design.id).sequence == "ACDEFG"
    assert not (project.root_dir / "PROJECT_CONTEXT.md").exists()
