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


def test_frontend_build_is_reused_when_current(tmp_path, monkeypatch):
    frontend = tmp_path / "frontend"
    source = frontend / "src"
    dist = frontend / "dist"
    source.mkdir(parents=True)
    dist.mkdir(parents=True)
    package = frontend / "package.json"
    component = source / "App.tsx"
    index = dist / "index.html"
    package.write_text("{}", encoding="utf-8")
    component.write_text("export default null", encoding="utf-8")
    index.write_text("<html></html>", encoding="utf-8")

    package.touch()
    component.touch()
    index.touch()
    future = index.stat().st_mtime + 5
    launcher.os.utime(index, (future, future))

    monkeypatch.setattr(launcher, "FRONTEND_DIR", frontend)
    monkeypatch.setattr(launcher, "FRONTEND_DIST", dist)
    assert launcher.frontend_build_is_current() is True


def test_ensure_frontend_build_installs_and_builds_on_first_launch(tmp_path, monkeypatch):
    frontend = tmp_path / "frontend"
    source = frontend / "src"
    dist = frontend / "dist"
    source.mkdir(parents=True)
    (frontend / "package.json").write_text("{}", encoding="utf-8")
    (source / "App.tsx").write_text("export default null", encoding="utf-8")

    monkeypatch.setattr(launcher, "FRONTEND_DIR", frontend)
    monkeypatch.setattr(launcher, "FRONTEND_DIST", dist)
    monkeypatch.setattr(launcher.shutil, "which", lambda name: "/usr/bin/npm" if name == "npm" else None)

    calls = []

    def fake_run(command, cwd, check):
        calls.append((command, cwd, check))
        if command[-1] == "build":
            dist.mkdir(parents=True, exist_ok=True)
            (dist / "index.html").write_text("<html></html>", encoding="utf-8")

    monkeypatch.setattr(launcher.subprocess, "run", fake_run)

    result = launcher.ensure_frontend_build()

    assert result == dist
    assert calls[0][0][-1] == "install"
    assert calls[1][0][-2:] == ["run", "build"]
