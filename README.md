# Human-Guided Protein Design

An interactive PyRosetta prototype for human-in-the-loop protein design with persistent scientific provenance.

- **Status:** v0.3.0 — Scientific Design Archive & Provenance Layer
- **Current benchmark:** GB1 / Protein G B1 domain (1PGA)
- **Goal:** Let a human propose point mutations, receive controlled and interpretable structural-energy feedback, record the scientific reasoning behind each decision, preserve every explored design branch, and accumulate computational and experimental evidence over time.

---

## What v0.3 Adds

v0.3 changes the project from a session-based mutation evaluator into a persistent protein-design research archive.

v0.2 could answer:

> What happened during this mutation session?

v0.3 is designed to answer broader questions such as:

- Which designs have been explored?
- Which mutations were accepted or rejected?
- What sequence background was a mutation tested on?
- Which design did a later branch originate from?
- What did Rosetta predict at the time?
- Why did the human accept or reject the candidate?
- What experimental evidence was added later?
- Which files belong to a specific design?
- Can an old rejected branch be reopened and explored again?
- What is the complete scientific history of a design after months or years of work?

The central v0.3 idea is:

```text
Design
  ↓
Lineage
  ↓
Evidence
  ↓
Human decision
  ↓
More evidence over time
  ↓
New branches / reconsideration
```

The human remains the decision-maker. The software records and organizes evidence, but does not automatically decide which design is scientifically best.

---

## Core Design Principle

v0.3 separates four concepts that may coincide during a simple run but are not scientifically identical:

```text
Design       = what sequence/structure existed
Evidence     = what was observed or calculated
Decision     = what the human concluded at a particular time
Status       = whether the design is currently being pursued
```

For example, a design can be:

```text
accepted + active
accepted + deprioritized
rejected + deprioritized
rejected + active
```

A design that was rejected in the past is not deleted. New evidence can be attached later, and the branch can be revisited without rewriting its history.

This is important for long-term research provenance.

---

## Current Human-Guided Workflow

```text
Choose starting design
       ↓
Human proposes mutation
       ↓
Record design name / hypothesis / objective
       ↓
       ├───────────────────────────────┐
       │                               │
       ↓                               ↓
Prepare reference structure      Create point mutation
       │                               │
       │                         Local preparation
       │                               │
       └───────────────┬───────────────┘
                       ↓
            Compare prepared structures
                       ↓
             Rosetta full-atom scoring
                       ↓
        ΔScore + energy-term differences
                       ↓
              Structural context
                       ↓
       Conservative score interpretation
                       ↓
             Human accepts or rejects
                       ↓
               Record rationale
                       ↓
     Preserve design + evidence + decision
                       ↓
          Continue from chosen branch
```

Local preparation currently consists of:

```text
Local side-chain repacking (~8 Å)
       ↓
Local χ minimization (~8 Å)
       ↓
Restricted backbone minimization (i-1, i, i+1)
```

Reference and mutant structures receive the same preparation protocol before comparison.

---

## Design Lineage and Branching

Designs are stored as a tree.

Example:

```text
WT
└── L5W
    ├── L7N
    ├── W5I
    └── G9K
```

A mutation is interpreted relative to its direct parent.

For example:

```text
WT -> L5W -> +L7N
```

means that `L7N` was evaluated on the already mutated `L5W` background.

Therefore the reported ΔScore for `L7N` corresponds to:

```text
Score(L5W + L7N)
-
Score(L5W)
```

and not:

```text
Score(L7N)
-
Score(WT)
```

This preserves context dependence and makes the archive suitable for studying mutation interactions and epistasis-like effects.

Any saved design branch can later be selected as the starting point of a new session, including a previously rejected branch.

---

## Evidence Model

Evidence is organized into four simple categories:

```text
computational
experimental
literature
note
```

The specific method is stored separately.

Examples:

```text
Type: computational
Method: PyRosetta
```

```text
Type: experimental
Method: SPR
```

```text
Type: experimental
Method: NMR
```

```text
Type: experimental
Method: SEC
```

```text
Type: literature
Method: paper / database / reference
```

This avoids forcing the user to decide whether, for example, SPR should be classified as biochemical or biophysical, or whether NMR belongs under spectroscopy or structural analysis.

Evidence can be added long after the design was created.

The long-term goal is that one design can accumulate:

```text
PyRosetta
ProteinMPNN
AlphaFold
SPR
SEC
CD
MALS
NMR
purification results
literature
human notes
```

inside the same scientific record.

---

## Portable Evidence Storage

External files can be copied into the project so that the archive does not depend on arbitrary paths elsewhere on the computer.

For example:

```text
data/projects/gb1_design/
└── evidence/
    ├── computational/
    ├── experimental/
    │   ├── NMR/
    │   ├── SPR/
    │   ├── SEC/
    │   └── CD/
    ├── literature/
    └── note/
```

Evidence entries store project-relative paths when files are imported into the project.

This makes the project easier to move, archive, back up, or share.

---

## Canonical Archive vs Human-Readable Views

The canonical scientific record is:

```text
design_archive.json
```

This file stores the complete machine-readable project state.

Human-readable views are generated from it:

```text
design_archive.json
        ↓
        ├── PROJECT_SUMMARY.md
        ├── terminal project tree
        ├── terminal design review
        └── Obsidian Markdown vault
```

The generated Markdown files are views of the archive, not the source of truth.

For v0.3, the intended direction is:

```text
design_archive.json
        ↓
generated views
```

not bidirectional synchronization.

---

## Current Features

### Mutation evaluation

- Load and score GB1 (1PGA, 56 residues).
- Generate point mutations without relying on the crashing `MutateResidue.apply()` path encountered during development.
- Preserve the current design while evaluating a candidate.
- Apply the same local preparation protocol to reference and mutant structures.
- Extract selected weighted Rosetta energy terms.
- Calculate per-term energy differences.
- Classify meaningful favorable and unfavorable score-term changes.
- Ignore negligible numerical differences using an energy tolerance.
- Provide conservative human-readable interpretations.
- Report structural neighbors within the configured radius.
- Repack residues in an approximately 8 Å neighborhood.
- Perform local χ minimization.
- Restrict backbone minimization to `i-1, i, i+1`.
- Evaluate all 19 substitutions at a selected position.
- Rank mutation scans by ΔScore.
- Use deterministic PyRosetta sampling during development.

### Human-guided design

- Interactive terminal-based design workflow.
- Validate mutation input before evaluation.
- Give designs human-readable names.
- Record hypothesis and objective before evaluation.
- Accept or reject the candidate after reviewing the result.
- Record the human rationale for the decision.
- Continue from the accepted structure during a session.
- Start later sessions from any saved design branch.
- Preserve rejected candidates rather than deleting them.
- Preserve the complete sequence of every design node.
- Track parent-child lineage across sessions.

### Scientific provenance

- Persistent project-level `design_archive.json`.
- Unique IDs for designs, evidence entries, and decisions.
- Append scientific decisions without deleting earlier history.
- Store design status separately from decision outcome.
- Store full-precision numerical values in the archive.
- Display Rosetta values rounded to two decimals for readability.
- Save each evaluated design structure as PDB.
- Support human-readable PDB filenames.
- Preserve rejected-design structures.
- Autosave the archive during the workflow.
- Reload the project across separate runs.

### External evidence

- Add computational, experimental, literature, and note evidence.
- Attach evidence to any archived design.
- Import arbitrary research files.
- Copy evidence files into the project for portability.
- Preserve evidence added months or years after a design decision.
- Review all evidence associated with one design.

### Project views

- Print the complete design tree in the terminal.
- Review one design in detail.
- Generate project-wide statistics and evidence summaries.
- Generate `PROJECT_SUMMARY.md`.
- Export linked Markdown design notes for Obsidian.
- Preserve links between parent and child designs.
- Highlight accumulated sequence mutations in generated Markdown views.

---

## Current Test System

- **PDB:** 1PGA
- **Length:** 56 residues
- **Sequence:** `MTYKLILNGKTLKGETTTEAVDAATAEKVFKQYANDNGVDGEWTYDDATKTFTVTE`
- **RCSB:** https://www.rcsb.org/structure/1PGA

GB1 remains the development benchmark for v0.3. The archive architecture is intended to support larger design projects later.

---

## Score Terms

Current Rosetta feedback includes:

- `total_score`
- `fa_atr`
- `fa_rep`
- `fa_sol`
- `fa_elec`
- `hbond_sr_bb`
- `hbond_lr_bb`
- `hbond_bb_sc`
- `hbond_sc`

The displayed terms are selected components of the complete Rosetta score function and are not expected to sum exactly to `total_score`.

### Interpretation of ΔScore

The mutation comparison is:

```text
ΔScore =
Score(prepared mutant)
-
Score(prepared reference)
```

Therefore:

- **Negative:** More favorable under the current Rosetta protocol
- **Near zero:** Similar to the reference
- **Positive:** Less favorable under the current Rosetta protocol

ΔScore is reported in **Rosetta Energy Units (REU)**.

It should not be interpreted directly as an experimental folding free-energy difference or experimental ΔΔG.

Small differences should not be overinterpreted.

### Numerical precision

Rosetta calculations and archived values retain their normal floating-point precision.

Human-facing terminal and Markdown views display scores rounded to approximately two decimal places for readability.

---

## Energy-Term Interpretation

The interpretation layer describes the direction of individual Rosetta score components conservatively.

Example:

```text
fa_atr   -5.05   More favorable attractive atomic interactions.
fa_rep   +5.05   Increased steric repulsion.
fa_sol   +3.49   Less favorable implicit-solvation contribution.
```

The program does not conclude from these terms alone that a mutation is biologically beneficial, experimentally stabilizing, or experimentally destabilizing.

The final decision remains human-guided.

---

## Structural Context

The workflow reports residues neighboring the proposed mutation within the configured structural radius.

Example:

```text
Nearby residues
--------------------------------------------------
F52        4.75 Å
F30        4.78 Å
T16        5.16 Å
K4         5.63 Å
```

The neighborhood is defined spatially in the folded structure rather than only by primary-sequence proximity.

This allows residues that are distant in sequence but close in three-dimensional space to contribute to the local mutation context.

---

# Scripts: 01 to 09

The scripts are intentionally separated by purpose. They range from basic validation of the PyRosetta setup to full project-level scientific review.

---

## `01_load_gb1.py` — Load and Score the Benchmark

### Purpose

Verify that PyRosetta initializes correctly, load GB1 from `1PGA.pdb`, inspect the sequence, and evaluate the starting structure with the configured score function.

### Why use it

Use this first when:

- installing or updating the environment;
- checking that PyRosetta still works;
- validating the input PDB;
- confirming that scoring is available before running more complex workflows.

### Run

```bash
python scripts/01_load_gb1.py
```

### Typical role

```text
environment check
      ↓
PDB loading
      ↓
basic scoring
```

This is the simplest smoke test in the repository.

---

## `02_mutation_scan.py` — Systematic Position Scan

### Purpose

Evaluate all 19 alternative amino-acid substitutions at a selected residue position.

Each candidate is prepared using the same local structural protocol and compared against a matched prepared reference.

### Why use it

Use this when you want a fast computational overview of a position before making a human-guided decision.

It is useful for questions such as:

- Which substitutions are energetically least unfavorable?
- Which substitutions introduce large steric penalties?
- Is the position tolerant to mutation?
- Which candidates are worth inspecting manually?

### Run

```bash
python scripts/02_mutation_scan.py
```

### Output

Mutation-scan results are stored under:

```text
data/results/mutation_scans/
```

### Important

The ranking is based on the current Rosetta protocol. It is evidence for human inspection, not an automatic design recommendation.

---

## `03_human_guided.py` — Main Interactive Design Workflow

### Purpose

Run the primary human-in-the-loop protein-design workflow.

This is the central script for interactive mutation design.

### What it does

The script can:

- create a new project from WT GB1;
- reopen an existing project;
- show available starting designs;
- continue from any saved design branch;
- load the PDB associated with that branch;
- ask for a mutation;
- ask for an optional human-readable design name;
- record the hypothesis;
- record the design objective;
- evaluate the candidate with PyRosetta;
- display ΔScore and selected energy-term changes;
- display nearby structural residues;
- provide conservative energy interpretation;
- ask the human to accept or reject;
- record the decision rationale;
- save the candidate structure whether accepted or rejected;
- update the design tree;
- autosave the project archive;
- preserve session-level CSV/JSON/PDB outputs.

### Why use it

Use this whenever you are actively designing and want the scientific record to grow with the experiment.

This is the normal entry point for iterative design work.

### Run

```bash
python scripts/03_human_guided.py
```

### Example lineage

```text
WT
└── L5W
    ├── L7N
    ├── W5I
    └── G9K
```

If you select `L7N` as the starting design and introduce `F30Y`, the new branch is:

```text
WT
└── L5W
    └── L7N
        └── F30Y
```

The effect of `F30Y` is evaluated relative to the `L5W + L7N` parent background.

### Session outputs

Individual sessions are stored under the project:

```text
data/projects/gb1_design/
└── sessions/
    └── session_YYYYMMDD_HHMMSS/
        ├── history.csv
        ├── history.json
        └── final_design.pdb
```

The project archive itself is not session-specific.

---

## `04_test_archive.py` — Archive Persistence Test

### Purpose

Test the v0.3 provenance model independently of the full PyRosetta workflow.

The script creates designs, evidence, and decisions; saves the archive; reloads it; and verifies that scientific history survives serialization.

### Why use it

Use this after modifying:

- archive models;
- JSON serialization;
- archive loading;
- decision history;
- evidence handling;
- lineage infrastructure.

It is a focused development/debugging script rather than a normal scientific workflow.

### Run

```bash
python scripts/04_test_archive.py
```

### What it validates

Conceptually:

```text
create archive
     ↓
add designs
     ↓
add evidence
     ↓
add decision
     ↓
save JSON
     ↓
reload JSON
     ↓
recover history
```

This is useful for catching provenance-layer regressions without having to run expensive PyRosetta calculations.

---

## `05_add_evidence.py` — Attach External Scientific Evidence

### Purpose

Add new evidence to an existing design.

### Supported evidence categories

```text
1. Computational
2. Experimental
3. Literature
4. Note
```

The specific technique or source is then entered separately, for example:

```text
SPR
NMR
SEC
CD
MALS
ProteinMPNN
AlphaFold
paper
lab notebook
```

### Why use it

Use this whenever information is generated outside the interactive PyRosetta session.

Examples:

- an SPR experiment is performed several months later;
- an NMR spectrum becomes available;
- a SEC chromatogram is collected;
- a ProteinMPNN result is generated externally;
- a paper changes the interpretation of a residue;
- you want to attach a research note to an old rejected branch.

### Run

```bash
python scripts/05_add_evidence.py
```

### File import

When a valid file path is supplied, the file can be copied into the project evidence directory.

Example:

```text
data/projects/gb1_design/
└── evidence/
    └── experimental/
        └── NMR/
            └── spectrum.png
```

The archive then stores a project-relative reference rather than relying on the original file remaining elsewhere on the computer.

### Important

Evidence can be attached to accepted, rejected, active, or deprioritized designs.

A rejected branch remains a valid scientific object.

---

## `06_review_design.py` — Review One Design in Detail

### Purpose

Inspect the complete scientific record for one selected design.

### What it shows

The review includes:

- design ID;
- human-readable name;
- lineage;
- accumulated mutations;
- current status;
- sequence;
- saved structure;
- full decision history;
- hypothesis;
- objective;
- rationale;
- computational evidence;
- experimental evidence;
- literature;
- notes;
- attached files;
- evidence counts.

### Why use it

Use this when returning to a design after time has passed and you want to answer:

> What exactly do we know about this design?

This is particularly useful once evidence has accumulated across multiple sessions or experimental campaigns.

### Run

```bash
python scripts/06_review_design.py
```

### Example

```text
DESIGN REVIEW

Lineage:
  WT -> L5W -> +L7N

Accumulated mutations:
  L5W, L7N

Decision:
  rejected

Evidence:
  PyRosetta
  NMR
  SPR
  note
```

---

## `07_project_tree.py` — View the Complete Design Tree

### Purpose

Print the complete design lineage graph as a terminal tree.

### Why use it

Use this for a fast project-wide overview.

It makes it easy to see:

- which branches exist;
- which designs were accepted;
- which were rejected;
- which branches remain active;
- Rosetta ΔScores;
- how much evidence is attached to each node.

### Run

```bash
python scripts/07_project_tree.py
```

### Example

```text
• WT (active)
└── ✓ L5W (active) Δ+14.99 [comp:1]
    ├── ✗ L7N (deprioritized) Δ+5.90 [comp:1, exp:1]
    ├── ✗ W5I (deprioritized) [comp:1]
    └── ✓ G9K (active) Δ+95.26 [comp:1]
```

The terminal tree is a lightweight precursor to the interactive graphical tree planned for a future frontend.

---

## `08_export_obsidian.py` — Export an Obsidian Vault

### Purpose

Generate linked Markdown notes from the canonical project archive.

### Why use it

Use this when you want to browse the project visually without building or launching a dedicated frontend.

Obsidian provides:

- clickable design links;
- backlinks;
- graph view;
- local graph view;
- search;
- tags;
- Markdown rendering.

### Run

```bash
python scripts/08_export_obsidian.py
```

### Output

```text
data/projects/gb1_design/
└── obsidian/
    └── Designs/
        ├── WT__....md
        ├── L5W__....md
        ├── L7N__....md
        └── ...
```

Each design note contains information such as:

- lineage links;
- sequence;
- accumulated mutations highlighted in blue;
- structure path;
- decision history;
- evidence;
- attached files;
- child-design links.

### Opening locally

The generated Markdown files can be previewed directly in VSCodium.

For a full network view, open:

```text
data/projects/gb1_design/obsidian/
```

as an Obsidian vault.

### Important

Do not treat the generated Obsidian notes as the canonical archive.

The intended workflow is:

```text
design_archive.json
        ↓
Obsidian export
```

Regenerate the vault when the canonical archive changes.

---

## `09_project_summary.py` — Project-Wide Scientific Summary

### Purpose

Generate a high-level summary of the entire project.

The script prints the summary to the terminal and writes a human-readable Markdown dashboard:

```text
data/projects/gb1_design/PROJECT_SUMMARY.md
```

### Why use it

Use this when:

- returning to the project after a long break;
- preparing for a meeting;
- deciding which designs need more evidence;
- reviewing accepted and rejected branches;
- checking how much computational or experimental work has accumulated;
- preparing material for a report, thesis, collaboration, or future frontend.

### Run

```bash
python scripts/09_project_summary.py
```

### Summary contents

The report includes:

- total number of designs;
- accepted designs;
- rejected designs;
- designs with no decision;
- computational evidence counts;
- experimental evidence counts;
- literature entries;
- notes;
- design lineages;
- current status;
- latest decision;
- latest Rosetta ΔScore where available;
- evidence methods;
- evidence gaps;
- detailed design records.

### Design philosophy

The summary intentionally does **not** calculate a universal "best design" score.

For example:

```text
Rosetta
SPR
SEC
NMR
literature
human rationale
```

cannot automatically be reduced to one scientifically universal metric.

The project summary organizes the evidence so that the human can make the decision.

---

## Recommended Script Workflow

For normal development and research use:

```text
01_load_gb1.py
      ↓
environment / benchmark check

02_mutation_scan.py
      ↓
optional position-level exploration

03_human_guided.py
      ↓
main design workflow

05_add_evidence.py
      ↓
add later computational or experimental results

06_review_design.py
      ↓
inspect one design deeply

07_project_tree.py
      ↓
inspect the complete lineage

08_export_obsidian.py
      ↓
visual linked-note exploration

09_project_summary.py
      ↓
project-wide human-readable report
```

`04_test_archive.py` is mainly a development/validation utility for the archive layer.

---

## Project Structure

The v0.3 layout is conceptually:

```text
HumanguidedProteinDesign/
├── data/
│   ├── raw/
│   │   └── 1PGA.pdb
│   ├── processed/
│   ├── results/
│   │   ├── mutation_scans/
│   │   └── human_guided_sessions/      # legacy / earlier session outputs
│   └── projects/
│       └── gb1_design/
│           ├── design_archive.json
│           ├── PROJECT_SUMMARY.md
│           ├── structures/
│           ├── evidence/
│           │   ├── computational/
│           │   ├── experimental/
│           │   ├── literature/
│           │   └── note/
│           ├── sessions/
│           └── obsidian/
│               └── Designs/
├── docs/
│   └── DEVELOPMENT_JOURNEY.md
├── scripts/
│   ├── 01_load_gb1.py
│   ├── 02_mutation_scan.py
│   ├── 03_human_guided.py
│   ├── 04_test_archive.py
│   ├── 05_add_evidence.py
│   ├── 06_review_design.py
│   ├── 07_project_tree.py
│   ├── 08_export_obsidian.py
│   └── 09_project_summary.py
├── src/
│   └── human_protein_design/
│       ├── __init__.py
│       ├── analysis.py
│       ├── context.py
│       ├── interpretation.py
│       ├── mutation.py
│       ├── scoring.py
│       ├── scan.py
│       ├── session.py
│       └── archive/
│           ├── __init__.py
│           ├── evidence.py
│           ├── models.py
│           ├── obsidian.py
│           ├── project.py
│           ├── store.py
│           └── summary.py
├── tests/
│   ├── test_analysis.py
│   ├── test_context.py
│   ├── test_interpretation.py
│   └── test_mutation.py
├── pyproject.toml
└── README.md
```

---

## Module Responsibilities

### Core protein-design modules

- `mutation.py` → residue replacement
- `scoring.py` → score function and weighted Rosetta energy extraction
- `scan.py` → local preparation and systematic mutation scans
- `analysis.py` → reference-vs-mutant energetic comparison
- `context.py` → structural neighborhood around a mutation
- `interpretation.py` → conservative human-readable interpretation of score changes
- `session.py` → interactive-session state, mutation evaluation, decisions, persistence hooks

### Archive modules

- `archive/models.py` → `Design`, `Decision`, and `EvidenceEntry` data models
- `archive/store.py` → canonical archive storage, loading, validation, lineage and evidence queries
- `archive/project.py` → persistent project-level directory and archive management
- `archive/evidence.py` → external evidence attachment and portable file import
- `archive/obsidian.py` → Obsidian-compatible linked Markdown export
- `archive/summary.py` → human-readable project summary generation

### Other

- `scripts/` → executable workflows and project utilities
- `tests/` → automated validation of core behavior

---

## Project Data Layout

The persistent project is stored under:

```text
data/projects/gb1_design/
```

### `design_archive.json`

Canonical scientific record.

It contains:

- designs;
- parent-child relationships;
- sequences;
- structure paths;
- statuses;
- decisions;
- hypotheses;
- objectives;
- rationales;
- computational evidence;
- experimental evidence;
- literature;
- notes;
- file references;
- timestamps.

The full archive is serialized when saved.

For v0.3 this is appropriate because the project remains small. A database or append-only event store can be considered later if archive size or concurrency becomes important.

### `PROJECT_SUMMARY.md`

Automatically generated human-readable project dashboard.

This is intended to be the quickest file to open when returning to the project after time away.

### `structures/`

Persistent structures for evaluated designs.

Accepted and rejected candidate structures are retained.

### `evidence/`

Portable copies of imported experimental, computational, literature, and note-related files.

### `sessions/`

Timestamped records of individual interactive design sessions.

Sessions are provenance records, but they do not own the canonical project archive.

### `obsidian/`

Generated linked Markdown representation of the project.

This can be opened directly as an Obsidian vault.

---

## Scientific Design Decisions

### Identical treatment of reference and mutant

Reference and mutant structures are evaluated using the same local preparation protocol before calculating ΔScore.

```text
Current design
       ├────────────────────────────┐
       │                            │
       ↓                            ↓
Prepare reference              Create mutation
       │                            │
       │                       Prepare mutant
       ↓                            ↓
Prepared reference             Prepared mutant
       │                            │
       └─────────── compare ────────┘
```

This prevents energetic changes caused simply by additional relaxation from being incorrectly attributed to the mutation.

### Spatial rather than sequence-local repacking

The packing neighborhood is defined in three-dimensional space around the mutation.

This captures residues that may be distant in primary sequence but close in the folded structure.

### Conservative backbone motion

Side chains in the local neighborhood can relax, while backbone motion is restricted to residues immediately surrounding the mutation.

This limits excessive remodeling during point-mutation evaluation.

### Transparent score decomposition

Individual weighted Rosetta energy terms are preserved rather than reporting only a single total score.

The project also records how those terms change relative to the matched prepared reference.

### Reproducible development

Side-chain packing contains stochastic sampling.

Development runs therefore use a fixed Rosetta random seed so that repeated evaluations are reproducible during testing and debugging.

### Conservative interpretation

Rosetta score changes are treated as evidence rather than biological conclusions.

The program describes terms such as steric repulsion, attractive interactions, solvation, electrostatics, and hydrogen bonding while leaving the final decision to the human.

### Decisions are historical events

A rejection is not deletion.

An acceptance is not proof that the design is permanently optimal.

The archive preserves what was decided given the evidence available at that time.

### Status is separate from decision

A design's current status can change without erasing its historical decision record.

This supports future workflows such as:

```text
accepted → later deprioritized
rejected → later reactivated
active → later superseded
```

---

## Example Scientific History

A design can accumulate evidence over time:

```text
2026-08
PyRosetta design
      ↓
candidate rejected
      ↓
2026-10
new ProteinMPNN analysis
      ↓
2027-01
expression and SEC
      ↓
2027-03
SPR
      ↓
2027-05
NMR
      ↓
design reconsidered
```

All of these events can remain attached to the same design node.

This is one of the main motivations for the v0.3 archive architecture.

---

## Legacy Session Outputs

Earlier human-guided sessions may still exist under:

```text
data/results/human_guided_sessions/
```

These are useful historical v0.2 records.

v0.3 moves the primary long-term scientific state to:

```text
data/projects/gb1_design/
```

Old session data does not need to be deleted.

---

## Running

Basic environment check:

```bash
python scripts/01_load_gb1.py
```

Mutation scan:

```bash
python scripts/02_mutation_scan.py
```

Interactive design:

```bash
python scripts/03_human_guided.py
```

Archive development test:

```bash
python scripts/04_test_archive.py
```

Add external evidence:

```bash
python scripts/05_add_evidence.py
```

Review one design:

```bash
python scripts/06_review_design.py
```

View complete design tree:

```bash
python scripts/07_project_tree.py
```

Export Obsidian notes:

```bash
python scripts/08_export_obsidian.py
```

Generate and save the project summary:

```bash
python scripts/09_project_summary.py
```

Run automated tests:

```bash
pytest -q
```

---

## v0.3 Scope

v0.3 focuses on the **scientific memory and provenance layer**.

It deliberately does not yet attempt to provide a full graphical application.

The current interface is still primarily terminal-based, with Markdown and Obsidian providing human-readable views.

The next development stage can build an interactive workspace on top of the archive rather than redesigning the underlying scientific data model.

Conceptually:

```text
v0.2
Interpretable mutation evaluation
        ↓
v0.3
Persistent scientific provenance
        ↓
future interactive layer
Design tree + navigation + evidence visualization + frontend
```

---

## Development Status

v0.3 should be considered a research-prototype milestone rather than a production protein-design platform.

The current benchmark remains GB1, and Rosetta-based energetic interpretation remains deliberately conservative.

The important v0.3 advance is that the project can now preserve not only the final accepted sequence, but the **history of scientific exploration**:

```text
what was proposed
what sequence background it came from
what was calculated
what evidence was available
what the human expected
what the human decided
why the decision was made
what evidence arrived later
and where the project went next
```

That provenance layer is intended to support the future interactive design workspace.
