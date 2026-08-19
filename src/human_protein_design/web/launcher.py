"""Cross-platform launcher for the complete local HGD research workspace."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import webbrowser
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_DIR = REPOSITORY_ROOT / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"


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
    """Make a local PyMOL installation visible to the backend launcher."""
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


def _frontend_inputs() -> list[Path]:
    """Return files whose modification should invalidate the compiled frontend."""
    candidates = [
        FRONTEND_DIR / "package.json",
        FRONTEND_DIR / "package-lock.json",
        FRONTEND_DIR / "vite.config.ts",
        FRONTEND_DIR / "tsconfig.json",
        FRONTEND_DIR / "index.html",
    ]
    source_dir = FRONTEND_DIR / "src"
    if source_dir.is_dir():
        candidates.extend(path for path in source_dir.rglob("*") if path.is_file())
    return [path for path in candidates if path.is_file()]


def frontend_build_is_current() -> bool:
    """Return whether an existing React build is newer than its source files."""
    index = FRONTEND_DIST / "index.html"
    if not index.is_file():
        return False
    built_at = index.stat().st_mtime
    return all(path.stat().st_mtime <= built_at for path in _frontend_inputs())


def ensure_frontend_build() -> Path:
    """Build the React application when missing or stale.

    Normal users only run ``hgd``. Node/npm are part of the HGD environment, so
    the launcher can perform the one-time frontend setup automatically. Existing
    builds are reused until frontend source files change.
    """
    if frontend_build_is_current():
        return FRONTEND_DIST

    package_json = FRONTEND_DIR / "package.json"
    if not package_json.is_file():
        raise SystemExit(f"HGD frontend source was not found at {FRONTEND_DIR}.")

    npm = shutil.which("npm")
    if npm is None:
        raise SystemExit(
            "HGD needs npm to build the local interface. Update/create the environment from environment.yml and retry."
        )

    try:
        if not (FRONTEND_DIR / "node_modules").is_dir():
            print("HGD: installing frontend dependencies (first launch only)…")
            subprocess.run([npm, "install"], cwd=FRONTEND_DIR, check=True)
        print("HGD: building local interface…")
        subprocess.run([npm, "run", "build"], cwd=FRONTEND_DIR, check=True)
    except subprocess.CalledProcessError as error:
        raise SystemExit(f"HGD frontend build failed with exit code {error.returncode}.") from error

    index = FRONTEND_DIST / "index.html"
    if not index.is_file():
        raise SystemExit("HGD frontend build finished without creating frontend/dist/index.html.")
    return FRONTEND_DIST


def _open_browser(url: str) -> None:
    """Open HGD after Uvicorn has had a moment to bind its local socket."""
    try:
        webbrowser.open(url)
    except Exception:
        # Browser launch is convenience only; the terminal still prints the URL.
        pass


def main() -> None:
    """Build the UI if needed, then start the complete local HGD workspace."""
    try:
        import uvicorn
        from fastapi.staticfiles import StaticFiles
        from human_protein_design.web.api import app
    except ImportError as error:
        raise SystemExit('Install the web dependencies first: python -m pip install -e ".[web]"') from error

    frontend_dist = ensure_frontend_build()

    # API routes are already registered on ``app``. Mounting the compiled React
    # application afterwards makes it the fallback for normal browser requests
    # while /api/... keeps using the FastAPI endpoints above it.
    if not any(getattr(route, "name", None) == "hgd-frontend" for route in app.routes):
        app.mount(
            "/",
            StaticFiles(directory=str(frontend_dist), html=True),
            name="hgd-frontend",
        )

    pymol = prepare_pymol_for_backend()
    if pymol:
        print(f"HGD: PyMOL detected at {pymol}")
    else:
        print("HGD: PyMOL not detected. Structure files remain usable, but 'Open in PyMOL' will be unavailable.")
        print("     Install licensed PyMOL, set HGD_PYMOL, or install pymol-open-source.")

    host = "127.0.0.1"
    try:
        port = int(os.environ.get("HGD_PORT", "8000"))
    except ValueError as error:
        raise SystemExit("HGD_PORT must be an integer.") from error
    url = f"http://{host}:{port}"

    print(f"HGD: opening complete local workspace at {url}")
    print("HGD: press Ctrl+C to stop it.")
    if os.environ.get("HGD_NO_BROWSER", "").lower() not in {"1", "true", "yes"}:
        threading.Timer(1.0, _open_browser, args=(url,)).start()

    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
