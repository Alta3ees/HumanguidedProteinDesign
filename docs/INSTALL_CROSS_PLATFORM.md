# HGD local installation — Linux, macOS, Windows

Human-Guided Protein Design v0.4 is a **local-first** research workspace. Project sequences, structures, experimental files, notes, and evidence remain on the scientist's machine.

PyRosetta is a **core HGD dependency** because Rosetta mutation/evaluation is part of the main scientific workflow.

## 1. Supported platforms

Full HGD support targets:

- **Linux** — native
- **macOS** — native
- **Windows** — through **WSL2**

The Windows choice is deliberate: current PyRosetta distribution supports Windows through the Windows Linux layer rather than a native Windows Conda package. Running the full project inside WSL2 keeps the same Python/PyRosetta workflow used on Linux while still allowing the browser UI to be opened from Windows.

## 2. Create the HGD environment

From the repository root:

```bash
conda env create -f environment.yml
conda activate human-guided-protein-design
```

The environment installs Python 3.11, PyRosetta, PyMOL open source, Node.js 20+, HGD itself, FastAPI/Uvicorn, and the development test tooling.

Verify the scientific evaluator:

```bash
python -c "import pyrosetta; print(pyrosetta.__version__)"
python -m pytest -q
```

## 3. Start HGD

Normal users only need:

```bash
conda activate human-guided-protein-design
hgd
```

`hgd` now manages the whole local workspace:

```text
hgd
 ├─ checks the compiled React interface
 ├─ installs frontend packages on first launch if needed
 ├─ rebuilds the interface when frontend source changed
 ├─ starts FastAPI on 127.0.0.1
 ├─ serves the React interface from that same process
 └─ opens the workspace in the default browser
```

The default address is:

```text
http://127.0.0.1:8000
```

Press `Ctrl+C` in the terminal to stop HGD.

The first launch may take a little longer because frontend dependencies/build artifacts may need to be created. Later launches reuse the existing build until the frontend source changes.

For frontend development only, developers may still use Vite separately:

```bash
cd frontend
npm run dev
```

This is not required for normal HGD use.

To prevent automatic browser opening:

```bash
HGD_NO_BROWSER=1 hgd
```

To use a different local port:

```bash
HGD_PORT=8010 hgd
```

## 4. PyMOL

The standard HGD environment includes `pymol-open-source`. HGD also supports licensed/local PyMOL installations.

If PyMOL is installed somewhere unusual, override discovery:

```bash
export HGD_PYMOL="/absolute/path/to/pymol"
hgd
```

HGD only launches the selected executable; it does not manage PyMOL licensing.

## 5. Platform notes

### Linux

Run HGD from a normal host terminal. If HGD is started inside a Flatpak-hosted IDE terminal, the launcher attempts to bridge the PyMOL GUI back to the host with `flatpak-spawn --host`.

### macOS

HGD checks `PATH` and also recognizes:

```text
/Applications/PyMOL.app/Contents/MacOS/PyMOL
```

`HGD_PYMOL` can always override discovery.

### Windows

For the **full** HGD workflow, run HGD inside WSL2. The browser UI can still be opened from the Windows browser through localhost.

## 6. Local-data guarantee

By default HGD binds only to `127.0.0.1`. Imported files are copied into the selected project and stored using project-relative paths. HGD does not require a cloud account or upload scientific data to a remote service.
