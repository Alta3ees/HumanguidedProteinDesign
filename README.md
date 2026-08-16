# Human-Guided Protein Design

An interactive PyRosetta prototype for human-in-the-loop protein design.

- **Status:** v0.2.0 — Interpretable Mutation Analysis
- **Current benchmark:** GB1 / Protein G B1 domain (1PGA)
- **Goal:** Let a human propose point mutations, receive controlled and interpretable structural-energy feedback, and iteratively accept or reject mutations.

---

## Concept

The current workflow is:

```text
Current accepted structure
       ↓
Human proposes mutation
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
            Repeat from accepted structure
```

Local preparation currently consists of:

```text
Local side-chain repacking (~8 Å)
       ↓
Local χ minimization (~8 Å)
       ↓
Restricted backbone minimization (i-1, i, i+1)
```

The human remains the decision-maker. The program evaluates mutations and provides structural and energetic evidence, but does not automatically decide which mutations should be accepted.

---

## Current Features

- Load and score GB1 (1PGA, 56 residues).
- Generate point mutations without relying on the crashing `MutateResidue.apply()` path encountered in the development environment.
- Preserve the current accepted pose while evaluating proposed mutations.
- Apply the same local preparation protocol to the reference and mutant structures.
- Extract selected weighted Rosetta energy terms programmatically.
- Calculate per-term energy differences between reference and mutant structures.
- Classify meaningful favorable and unfavorable score-term changes.
- Ignore negligible numerical changes using an energy tolerance.
- Provide conservative human-readable interpretations of Rosetta energy changes.
- Report residues neighboring the mutation site within the configured structural radius.
- Repack only residues in an approximately 8 Å structural neighborhood.
- Minimize side chains locally while restricting backbone motion to `i-1, i, i+1`.
- Evaluate all 19 substitutions at a selected position.
- Rank mutations by `ΔScore = mutant_score - reference_score`.
- Run an interactive terminal-based human-guided design session.
- Accept or reject proposed mutations without modifying the accepted state unless explicitly accepted.
- Continue subsequent mutations from the last accepted structure.
- Use deterministic PyRosetta sampling during development for reproducible evaluations.
- Save accepted mutation history to CSV and JSON.
- Save the final accepted structure as PDB.
- Store each human-guided run in a timestamped session directory.
- Automated tests for mutation, energetic analysis, structural context, and interpretation.

---

## Current Test System

- **PDB:** 1PGA  
  https://www.rcsb.org/structure/1PGA
- **Length:** 56 residues
- **Sequence:** `MTYKLILNGKTLKGETTTEAVDAATAEKVFKQYANDNGVDGEWTYDDATKTFTVTE`

---

## Score Terms

The current feedback includes:

- `total_score`
- `fa_atr`
- `fa_rep`
- `fa_sol`
- `fa_elec`
- `hbond_sr_bb`
- `hbond_lr_bb`
- `hbond_bb_sc`
- `hbond_sc`

The displayed score terms are selected components of the complete Rosetta score function. They are not expected to sum exactly to `total_score`.

### Interpretation of ΔScore

The current mutation comparison is:

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

*Small differences should not be overinterpreted.*

---

## Energy-Term Interpretation

v0.2 adds a conservative interpretation layer for the selected Rosetta terms.

For example:

```text
fa_atr   -6.90   More favorable attractive atomic interactions.
fa_rep   +5.80   Increased steric repulsion.
fa_sol   +1.83   Less favorable implicit-solvation contribution.
```

The interpretation describes the direction of individual Rosetta score components only.

The program does not conclude from these values alone that a mutation is biologically beneficial, experimentally stabilizing, or destabilizing.

---

## Structural Context

The human-guided workflow now reports residues neighboring the proposed mutation within the configured structural radius.

Example:

```text
Nearby residues
--------------------------------------------------
I6        3.82 Å
K4        4.13 Å
Y3        5.47 Å
L7        6.01 Å
```

The neighborhood is defined spatially in the folded structure rather than only by sequence proximity.

This allows residues that are distant in primary sequence but close in three-dimensional space to be included in the mutation context.

---

## Project Structure

```text
HumanguidedProteinDesign/
├── data/
│   ├── raw/
│   │   └── 1PGA.pdb
│   └── results/
│       ├── mutation_scans/
│       └── human_guided_sessions/
├── docs/
│   └── DEVELOPMENT_JOURNEY.md
├── scripts/
│   ├── 01_load_gb1.py
│   ├── 02_mutation_scan.py
│   └── 03_human_guided.py
├── src/
│   └── human_protein_design/
│       ├── __init__.py
│       ├── analysis.py
│       ├── context.py
│       ├── interpretation.py
│       ├── mutation.py
│       ├── scoring.py
│       ├── scan.py
│       └── session.py
├── tests/
│   ├── test_analysis.py
│   ├── test_context.py
│   ├── test_interpretation.py
│   └── test_mutation.py
├── pyproject.toml
└── README.md
```

### Responsibilities

- `mutation.py` → residue replacement
- `scoring.py` → score function and weighted Rosetta energy extraction
- `scan.py` → local preparation and systematic mutation scans
- `analysis.py` → reference-vs-mutant energetic comparison
- `context.py` → structural neighborhood around a mutation
- `interpretation.py` → conservative human-readable interpretation of score changes
- `session.py` → interactive-session state, evaluation, acceptance, and history
- `scripts/` → executable workflows
- `tests/` → automated validation of core behavior

---

## Running

```bash
python scripts/01_load_gb1.py
python scripts/02_mutation_scan.py
python scripts/03_human_guided.py
```

Run the automated test suite with:

```bash
pytest -q
```

---

## Scientific Design Decisions

### Identical treatment of reference and mutant

Reference and mutant structures are evaluated using the same local preparation protocol before calculating ΔScore.

Conceptually:

```text
Current accepted structure
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

This prevents energetic improvements caused simply by additional relaxation from being incorrectly attributed to the mutation.

### Spatial rather than sequence-local repacking

The packing neighborhood is defined in three-dimensional space around the mutation.

This captures residues that may be distant in primary sequence but close in the folded protein structure.

### Conservative backbone motion

Side chains in the local neighborhood can relax, but backbone motion is limited to residues immediately around the mutation.

This reduces the risk that a single point mutation causes excessive structural remodeling during the local evaluation.

### Transparent score decomposition

Individual weighted Rosetta energy terms are preserved rather than reporting only a single total score.

v0.2 additionally reports how those terms change relative to the matched reference structure.

### Reproducible development

Side-chain packing contains stochastic sampling.

Development runs therefore use a fixed Rosetta random seed so that repeated evaluations on the same system are reproducible.

This is useful for testing and debugging the human-guided workflow.

### Conservative interpretation

Rosetta score changes are presented as evidence rather than biological conclusions.

The software describes changes in terms such as steric repulsion, attractive interactions, solvation, electrostatics, and hydrogen bonding, but leaves the final design decision to the human user.

---

## Example Development Observations

### Why relaxation matters

The first E42F experiment illustrated why structural preparation is necessary.

Immediately after direct residue replacement, the mutation produced a very large energetic penalty dominated by steric repulsion. After repacking and minimization, the penalty became much smaller.

This motivated a central rule:

> **Do not interpret the score of an unrelaxed residue replacement as mutation quality.**

### Why matched reference preparation matters

During development of v0.2, an early analysis implementation compared:

```text
unprepared reference
vs.
prepared mutant
```

This produced apparently strongly favorable mutations because part of the score improvement came from the additional structural relaxation rather than the mutation itself.

The comparison was therefore changed to:

```text
prepared reference
vs.
prepared mutant
```

using the same local preparation protocol on both branches.

This makes the reported ΔScore a controlled comparison under the current protocol.

---

## Output

Mutation scans are stored under:

```text
data/results/mutation_scans/
```

Human-guided sessions are stored under:

```text
data/results/human_guided_sessions/
└── session_YYYYMMDD_HHMMSS/
    ├── history.csv
    ├── history.json
    └── final_design.pdb
```

### `history.csv`

Tabular record of accepted mutations and their Rosetta scores.

A CSV file is created even when no mutations are accepted, keeping the session-output structure consistent.

### `history.json`

Structured representation of the accepted mutation history and final sequence.

This format is intended for persistence and future UI integration.

### `final_design.pdb`

The final accepted protein structure at the end of the session.

If no mutation is accepted, this corresponds to the unchanged starting design.
