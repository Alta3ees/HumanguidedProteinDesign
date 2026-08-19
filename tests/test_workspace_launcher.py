from pathlib import Path

from human_protein_design.web import launcher


def test_explicit_pymol_override_wins(tmp_path, monkeypatch):
    executable = tmp_path / "custom-pymol"
    executable.write_text("fake", encoding="utf-8")
    monkeypatch.setenv("HGD_PYMOL", str(executable))
    monkeypatch.setattr(launcher.shutil, "which", lambda _name: None)

    assert launcher.find_pymol() == executable.resolve()


def test_path_pymol_is_used_without_forcing_open_source(tmp_path, monkeypatch):
    executable = tmp_path / "pymol"
    executable.write_text("fake", encoding="utf-8")
    monkeypatch.delenv("HGD_PYMOL", raising=False)
    monkeypatch.setattr(launcher.shutil, "which", lambda name: str(executable) if name == "pymol" else None)

    assert launcher.find_pymol() == executable.resolve()


def test_flatpak_prepares_host_launcher_shim(tmp_path, monkeypatch):
    executable = tmp_path / "pymol"
    executable.write_text("fake", encoding="utf-8")
    shim_dir = tmp_path / "shim"
    shim_dir.mkdir()

    monkeypatch.setattr(launcher, "find_pymol", lambda: executable.resolve())
    monkeypatch.setattr(launcher.tempfile, "mkdtemp", lambda prefix: str(shim_dir))
    monkeypatch.setattr(Path, "exists", lambda self: True if str(self) == "/.flatpak-info" else self.is_file())
    monkeypatch.setenv("PATH", "/usr/bin")

    selected = launcher.prepare_pymol_for_backend()

    assert selected == executable.resolve()
    shim = shim_dir / "pymol"
    assert shim.is_file()
    assert "flatpak-spawn --host" in shim.read_text(encoding="utf-8")
    assert str(shim_dir) == launcher.os.environ["PATH"].split(launcher.os.pathsep)[0]
