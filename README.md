# Human-Guided Protein Design

**Human-Guided Protein Design (HGD)** is a 100% local, interactive research workspace for protein design scientists. It combines PyRosetta-guided mutation design, structural inspection, human decisions, experimental evidence, and long-term scientific provenance in one persistent project archive.

The human remains the decision-maker. HGD helps scientists evaluate designs, record why they acted on them, attach experimental results later, and return months or years afterward without losing the context behind earlier work.

## Status

**v0.4 development — interactive research workspace**

Current development benchmark: GB1 / Protein G B1 domain (1PGA).

## Core idea

```text
Scientific objective
        ↓
Starting design
        ↓
Structure(s) + evidence
        ↓
Human hypothesis
        ↓
PyRosetta evaluation / position scan
        ↓
Human Accept / Defer / Reject decision
        ↓
New child design in the lineage tree
        ↓
More computational / experimental / literature evidence over time
        ↓
Return later, compare designs, and continue from any branch
```

A rejected or deferred branch remains part of the scientific record. HGD never silently rewrites historical designs.

## v0.4 workspace

The browser workspace currently provides:

- local project creation and project switching;
- radial design-lineage navigation;
- a right-side summary for the currently selected design;
- full scientific records opened explicitly from the summary;
- persistent design, decision, structure, target, objective, and evidence records;
- sequence editing that creates a new child design instead of overwriting history;
- structure attachment and deletion;
- local PyMOL launch for PDB/CIF/mmCIF/ENT/PQR structures;
- PyRosetta baseline structure scoring;
- one-substitution PyRosetta evaluation with local repacking/minimization;
- saturation scans of all 19 alternative amino acids at one position;
- Rosetta score-term inspection and structural-neighborhood context;
- explicit design-to-design PyRosetta comparison using archived scores;
- Accept / Defer / Reject decisions with rationale;
- native previews for common scientific files including FASTA, CSV/TSV/XLSX, JSON, Rosetta `.sc`, PDF, images, Markdown/text, and structure files;
- arbitrary evidence attachment for unsupported/raw instrument formats;
- one portable Markdown export for giving the current project context to an LLM.

## Scientific archive

Each project has one canonical machine-readable record:

```text
data/projects/<project>/design_archive.json
```

It stores the complete current archive state, including IDs and links between:

```text
ProjectObjective
Target
Design
StructureModel
Decision
EvidenceEntry
```

Scientific files are copied into the project and referenced with project-relative paths where appropriate, making projects portable between machines.

## LLM-ready project export

HGD intentionally has a single Markdown export rather than maintaining a second note-taking system.

From the web workspace, use:

**Export context for LLM (.md)**

or from the CLI:

```bash
python scripts/08_project_context.py
```

This generates:

```text
data/projects/<project>/PROJECT_CONTEXT.md
```

`PROJECT_CONTEXT.md` contains:

- project overview;
- objectives and targets;
- design index and lineage;
- sequences and design metadata;
- structures and confidence metadata;
- complete decision history;
- evidence summaries, files, references, and structured numerical data;
- a final JSON appendix containing the complete canonical archive state at export time.

The Markdown file is a portable snapshot. `design_archive.json` remains the source of truth.

## Installation

Full HGD currently targets:

- **Linux** — native;
- **macOS** — native;
- **Windows** — WSL2 for the complete PyRosetta workflow.

From the repository root:

```bash
conda env create -f environment.yml
conda activate human-guided-protein-design
```

The project environment includes Python 3.11, PyRosetta, PyMOL open-source as the default viewer, Node.js for building the web workspace, the local FastAPI backend, and test tooling.

A scientist with a licensed PyMOL installation may point HGD to that executable with `HGD_PYMOL`; HGD does not depend on which PyMOL edition is used.

Detailed platform notes are in [`docs/INSTALL_CROSS_PLATFORM.md`](docs/INSTALL_CROSS_PLATFORM.md).

## Start HGD

For normal scientific use there is **one command**:

```bash
conda activate human-guided-protein-design
hgd
```

`hgd` handles the complete local workspace:

```text
hgd
 ├─ detects/builds the React frontend when needed
 ├─ starts the local FastAPI backend
 ├─ serves the compiled frontend and API from the same process
 └─ opens http://127.0.0.1:8000 in the default browser
```

You do **not** need a second terminal, `uvicorn`, or `npm run dev` for normal use.

The first launch after a fresh clone or frontend change may take longer because HGD installs/builds the frontend assets. Later launches reuse the built frontend until the source changes.

Useful optional launcher settings:

```bash
HGD_NO_BROWSER=1 hgd
HGD_PORT=8010 hgd
```

### Frontend development only

Developers who specifically want Vite hot reload can still run:

```bash
cd frontend
npm install
npm run dev
```

That is a development workflow, not an end-user requirement.

All scientific project data remains on the local machine. HGD binds to the local interface and the browser communicates with the local Python API.

## Typical web workflow

```text
1. Create/select project
2. Click a design node to select it
3. Read its summary in the right inspector
4. Open the full scientific record only when deeper inspection/editing is needed
5. Attach the structure representing that design
6. Optionally score the current structure
7. Either:
      - evaluate one hypothesis-driven mutation, or
      - scan all 19 substitutions at one position
8. Inspect ΔScore, score terms, and structural context
9. Accept / Defer / Reject
10. HGD preserves the candidate as a child node
11. Attach later experimental/computational/literature evidence
12. Compare scored Design A against scored Design B explicitly
13. Continue from any branch months or years later
```

## Comparing designs

HGD distinguishes two different questions:

### Mutation evaluation

During a point-mutation experiment, HGD reports the candidate relative to the **specific parent design used for that mutation**:

```text
ΔScore = Score(prepared mutant) - Score(prepared parent)
```

The parent is not assumed to be WT. If you mutate an already mutated branch, the score is relative to that direct parent background.

### Design-to-design comparison

For broader comparison, HGD can compare two existing designs explicitly:

```text
Design A score
vs
Design B score

comparison = Score(B) - Score(A)
```

Both designs must already have an archived PyRosetta score belonging to that design. Mutation-generated designs receive their PyRosetta design score automatically; other designs can be scored from their scientific record with **Score current structure**.

The comparison UI always names **Design A** and **Design B**, shows the archived score source used for each, and never silently treats WT as the reference.

## Important Rosetta interpretation

Under the current Rosetta protocol:

- negative energetic differences are more favorable;
- near-zero differences are similar;
- positive energetic differences are less favorable.

These values are Rosetta Energy Units (REU), not experimental ΔΔG values. A favorable Rosetta score is evidence for human interpretation, not an automatic biological conclusion.

Absolute scores from independently prepared structures should also be interpreted cautiously. HGD shows the evidence source and protocol context so scientists can decide whether a particular A/B comparison is scientifically appropriate.

## Evidence model

Evidence uses four intentionally broad categories:

```text
computational
experimental
literature
note
```

The method/source is stored separately, for example:

```text
computational · PyRosetta
computational · AlphaFold
computational · ProteinMPNN
experimental · SEC
experimental · SPR
experimental · CD
literature · paper
note · scientist observation
```

HGD accepts arbitrary files even when it cannot preview their format.

## CLI utilities

The web workspace is the main v0.4 interface. CLI scripts remain useful for development, validation, and direct scientific workflows.

| Script | Purpose |
|---|---|
| `00_new_project.py` | Create a project from sequence/target inputs |
| `01_load_gb1.py` | PyRosetta/GB1 smoke test and baseline scoring |
| `02_mutation_scan.py` | CLI saturation scan at one residue |
| `03_human_guided.py` | CLI human-guided mutation workflow |
| `04_test_archive.py` | Archive persistence developer test |
| `05_add_evidence.py` | Attach evidence from the CLI |
| `06_review_design.py` | Review one archived design |
| `07_project_tree.py` | Print the project lineage tree |
| `08_project_context.py` | Generate `PROJECT_CONTEXT.md` for human/LLM use |
| `10_add_structure.py` | Register a structure model |
| `11_register_generated_design.py` | Register an externally generated design |

## Tests

Run the Python suite:

```bash
python -m pytest -q
```

Build-check the frontend:

```bash
cd frontend
npm install
npm run build
```

The cross-platform CI checks the portable workspace on supported operating-system runners, while full PyRosetta support is validated on platforms where the scientific stack is available natively.

## Project principles

1. **Human-guided, not auto-decided.** Computational scores inform decisions; they do not replace them.
2. **History is append-oriented.** New designs become new nodes rather than overwriting old states.
3. **Structure is optional at the archive level.** It becomes required only for structure-based PyRosetta operations.
4. **Evidence accumulates over time.** Computational, experimental, literature, and human evidence can coexist on one design.
5. **Local first.** Project data and imported scientific files stay on the scientist's machine by default.
6. **One canonical archive.** Generated views such as `PROJECT_CONTEXT.md` are exports, not competing sources of truth.
7. **Comparisons are explicit.** HGD names the actual reference and comparison design instead of silently assuming WT.

## Repository layout

```text
src/human_protein_design/   Python package, archive, PyRosetta logic, local API
frontend/                   React + TypeScript workspace
scripts/                    CLI utilities
tests/                      Python tests
docs/                       installation/frontend notes
data/projects/              local scientific projects (not for public commits)
```

## License

See [`LICENSE`](LICENSE).
