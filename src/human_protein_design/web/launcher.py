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


def prepare_pymol_for_backend() -> Path | None:
    """Make the selected PyMOL visible to the existing backend launcher.

    HGD's API intentionally only asks for a ``pymol`` command. This helper
    discovers licensed/open-source installations and, when required, adds a
    tiny temporary shim directory to PATH. Inside Flatpak it uses
    ``flatpak-spawn --host`` so the GUI is launched on the real desktop.
    """
    pymol = find_pymol()
    if pymol is None:
        return None

    flatpak = Path("/.flatpak-info").exists()
    needs_shim = flatpak or (sys.platform == "darwin" and pymol.name != "pymol")

    if needs_shim and os.name != "nt":
        shim_dir = Path(tempfile.mkdtemp(prefix="hgd-pymol-"))
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
        print("     Install your licensed PyMOL, set HGD_PYMOL, or install pymol-open-source.")

    print("HGD: starting local workspace backend at http://127.0.0.1:8000")
    uvicorn.run(
        "human_protein_design.web.api:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
