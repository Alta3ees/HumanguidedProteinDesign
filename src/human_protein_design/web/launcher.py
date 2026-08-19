"""Cross-platform launcher for the local HGD research workspace."""

from __future__ import annotations

import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path


def _candidate_pymol_paths() -> list[Path]:
    """Return plausible local PyMOL executables for the current platform."""
    candidates: list[Path] = []

    configured = os.environ.get("HGD_PYMOL")
    if configured:
        candidates.append(Path(configured).expanduser())

    if sys.platform == "darwin":
        candidates.extend(
            [
                Path("/Applications/PyMOL.app/Contents/MacOS/PyMOL"),
                Path.home() / "Applications/PyMOL.app/Contents/MacOS/PyMOL",
            ]
        )
    elif os.name == "nt":
        roots = [
            os.environ.get("PROGRAMFILES"),
            os.environ.get("PROGRAMFILES(X86)"),
            os.environ.get("LOCALAPPDATA"),
        ]
        for root in filter(None, roots):
            base = Path(root)
            candidates.extend(
                [
                    base / "PyMOL" / "PyMOL.exe",
                    base / "PyMOL" / "PyMOLWin.exe",
                    base / "Schrodinger" / "PyMOL" / "PyMOL.exe",
                    base / "Schrodinger" / "PyMOL" / "PyMOLWin.exe",
                ]
            )

    return candidates


def find_pymol() -> Path | None:
    """Find an installed licensed or open-source PyMOL executable."""
    configured = os.environ.get("HGD_PYMOL")
    if configured:
        path = Path(configured).expanduser().resolve()
        if path.is_file():
            return path

    discovered = shutil.which("pymol")
    if discovered:
        return Path(discovered).resolve()

    for candidate in _candidate_pymol_paths():
        if candidate.is_file():
            return candidate.resolve()
    return None


def _write_posix_shim(directory: Path, pymol: Path, *, flatpak_host: bool) -> Path:
    shim = directory / "pymol"
    quoted = str(pymol).replace("'", "'\"'\"'")
    if flatpak_host:
        body = f"#!/bin/sh\nexec flatpak-spawn --host '{quoted}' \"$@\"\n"
    else:
        body = f"#!/bin/sh\nexec '{quoted}' \"$@\"\n"
    shim.write_text(body, encoding="utf-8")
    shim.chmod(shim.stat().st_mode | stat.S_IXUSR)
    return shim


def _write_windows_shim(directory: Path, pymol: Path) -> Path:
    """Expose executables such as PyMOLWin.exe under the command name pymol."""
    shim = directory / "pymol.cmd"
    target = str(pymol).replace('"', '""')
    shim.write_text(f'@echo off\r\n"{target}" %*\r\n', encoding="utf-8")
    return shim


def prepare_pymol_for_backend() -> Path | None:
    """Make a local PyMOL installation visible to the backend launcher.

    HGD accepts licensed or open-source PyMOL. The user can select an exact
    executable with ``HGD_PYMOL``. macOS application bundles and Windows
    ``PyMOLWin.exe`` installs are normalized to the ``pymol`` command expected
    by the API. When HGD itself runs inside Flatpak on Linux, a small shim uses
    ``flatpak-spawn --host`` so the GUI opens on the real desktop.
    """
    pymol = find_pymol()
    if pymol is None:
        return None

    flatpak = Path("/.flatpak-info").exists()
    mac_bundle_name = sys.platform == "darwin" and pymol.name != "pymol"
    windows_nonstandard_name = os.name == "nt" and pymol.stem.lower() != "pymol"
    needs_shim = flatpak or mac_bundle_name or windows_nonstandard_name

    if needs_shim:
        shim_dir = Path(tempfile.mkdtemp(prefix="hgd-pymol-"))
        if os.name == "nt":
            _write_windows_shim(shim_dir, pymol)
        else:
            _write_posix_shim(shim_dir, pymol, flatpak_host=flatpak)
        os.environ["PATH"] = str(shim_dir) + os.pathsep + os.environ.get("PATH", "")
    else:
        os.environ["PATH"] = str(pymol.parent) + os.pathsep + os.environ.get("PATH", "")

    return pymol


def main() -> None:
    """Start the local HGD API with platform-aware PyMOL discovery."""
    try:
        import uvicorn
    except ImportError as error:
        raise SystemExit('Install the web dependencies first: python -m pip install -e ".[web]"') from error

    pymol = prepare_pymol_for_backend()
    if pymol:
        print(f"HGD: PyMOL detected at {pymol}")
    else:
        print("HGD: PyMOL not detected. Structure files remain usable, but 'Open in PyMOL' will be unavailable.")
        print("     Install licensed PyMOL, set HGD_PYMOL, or install pymol-open-source.")

    print("HGD: starting local workspace backend at http://127.0.0.1:8000")
    uvicorn.run(
        "human_protein_design.web.api:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
