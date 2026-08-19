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

The environment installs:

- Python 3.11
- PyRosetta
- Node.js 20+
- HGD itself
- FastAPI / Uvicorn / web dependencies
- pytest / development test tooling

Verify the scientific evaluator immediately:

```bash
python -c "import pyrosetta; print(pyrosetta.__version__)"
```

Then verify the project:

```bash
python -m pytest -q
```

## 3. PyMOL is external and edition-independent

HGD does **not** force a specific PyMOL edition.

If `pymol` is already available, HGD uses it. This may be:

- licensed Schrödinger / Incentive PyMOL;
- open-source PyMOL;
- another local PyMOL installation exposed on `PATH`.

If PyMOL is installed somewhere unusual, point HGD to it before starting the workspace.

### Linux / macOS

```bash
export HGD_PYMOL="/absolute/path/to/pymol"
hgd
```

### Windows / WSL2

Run HGD inside WSL2. If PyMOL is installed inside the WSL environment and exposed on `PATH`, HGD uses it normally. External-viewer behavior can be configured separately as needed for a tester's Windows setup.

If no PyMOL is installed and the open-source build is desired:

```bash
conda install -c conda-forge pymol-open-source
```

Licensed users may instead install/use the official Schrödinger distribution. HGD only launches the executable; it does not manage or inspect the PyMOL license.

## 4. Start HGD

After activating the environment:

```bash
hgd
```

This starts the local API at:

```text
http://127.0.0.1:8000
```

For frontend development, use a second terminal:

```bash
cd frontend
npm install
npm run dev
```

and open:

```text
http://localhost:5173
```

The production goal is for a built frontend to be served directly by HGD so normal scientists do not need to run npm during everyday use.

## 5. Platform notes

### Linux

Run the HGD backend from a normal host terminal. If HGD is started inside a Flatpak-hosted IDE terminal, the `hgd` launcher attempts to bridge PyMOL GUI launch back to the host using `flatpak-spawn --host`.

### macOS

HGD checks `PATH` first and also recognizes the standard application bundle executable:

```text
/Applications/PyMOL.app/Contents/MacOS/PyMOL
```

`HGD_PYMOL` can always override discovery.

### Windows

For the **full** HGD workflow, install and run the project in WSL2. This is the supported route for PyRosetta-backed HGD on Windows.

The browser UI can still be opened from the Windows browser through localhost. Native-Windows-only testing may be useful for the structure-independent web/archive layer, but it is not considered the complete HGD scientific installation.

## 6. Local-data guarantee

By default HGD binds its backend only to `127.0.0.1`. Imported files are copied into the selected project and stored using project-relative paths. HGD does not require a cloud account or upload scientific data to a remote service.
