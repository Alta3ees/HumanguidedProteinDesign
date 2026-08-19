# HGD local installation — Linux, macOS, Windows

Human-Guided Protein Design v0.4 is designed as a **local-first** research workspace. Project sequences, structures, experimental files, notes, and evidence remain on the scientist's machine.

## 1. Create the core environment

The same core environment file is used on Linux, macOS, and Windows:

```bash
conda env create -f environment.yml
conda activate human-guided-protein-design
```

For an existing development environment:

```bash
python -m pip install -e ".[web]"
```

## 2. PyMOL is optional and not edition-locked

HGD does **not** require a specific PyMOL edition.

If `pymol` is already available, HGD uses it. This may be:

- licensed Schrödinger / Incentive PyMOL;
- open-source PyMOL;
- another local PyMOL installation exposed on `PATH`.

If PyMOL is installed somewhere unusual, point HGD to it before starting the workspace:

### Linux / macOS

```bash
export HGD_PYMOL="/absolute/path/to/pymol"
hgd
```

### Windows PowerShell

```powershell
$env:HGD_PYMOL = "C:\Path\To\PyMOL.exe"
hgd
```

If no PyMOL is installed and the open-source build is desired:

```bash
conda install -c conda-forge pymol-open-source
```

Licensed users may instead install/use the official Schrödinger distribution. HGD only launches the executable; it does not manage or inspect the PyMOL license.

## 3. Start HGD

After installing the package with the web extra, use the same command on all three platforms:

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

## 4. Platform notes

### Linux

Run the HGD backend from a normal host terminal. If HGD is started inside a Flatpak-hosted IDE terminal, the `hgd` launcher attempts to bridge PyMOL GUI launch back to the host using `flatpak-spawn --host`.

### macOS

HGD checks `PATH` first and also recognizes the standard application bundle executable:

```text
/Applications/PyMOL.app/Contents/MacOS/PyMOL
```

`HGD_PYMOL` can always override discovery.

### Windows

HGD checks `PATH` and common PyMOL installation locations. If an installer did not expose PyMOL on `PATH`, set `HGD_PYMOL` to `PyMOL.exe` / the local PyMOL executable.

## 5. PyRosetta

The archive, frontend, project management, evidence import, structure registration, and local PyMOL integration do not require PyRosetta.

PyRosetta-dependent mutation/evaluation workflows require a PyRosetta build compatible with the scientist's operating system and Python environment. PyRosetta remains a separate installation because its distribution mechanism is not a normal conda-forge/PyPI dependency.

Verify it independently with:

```bash
python -c "import pyrosetta; print(pyrosetta.__version__)"
```

## 6. Local-data guarantee

By default HGD binds its backend only to `127.0.0.1`. Imported files are copied into the selected project and stored using project-relative paths. HGD does not require a cloud account or upload scientific data to a remote service.
