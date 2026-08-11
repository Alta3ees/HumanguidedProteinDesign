# Human-Guided Protein Design

An interactive PyRosetta prototype for human-in-the-loop protein design.

- **Status:** V0 research prototype
- **Current benchmark:** GB1 / Protein G B1 domain (1PGA)
- **Goal:** Let a human propose point mutations, receive interpretable structural-energy feedback, and iteratively accept or reject mutations.

---

## Concept

The V0 workflow is:

```text
Current structure
       ↓
Human proposes mutation
       ↓
Point mutation
       ↓
Local side-chain repacking (~8 Å)
       ↓
Local χ minimization (~8 Å)
       ↓
Restricted backbone minimization (i-1, i, i+1)
       ↓
Rosetta full-atom scoring
       ↓
ΔScore + energy-term feedback
       ↓
Human accepts or rejects
       ↓
Repeat from accepted structure
```

The human remains the decision-maker. The program evaluates mutations but does not automatically decide which sequence should be accepted.

---

## Current Features

- Load and score GB1 (1PGA, 56 residues).
- Generate point mutations without relying on the crashing `MutateResidue.apply()` path encountered in the development environment.
- Extract selected weighted Rosetta energy terms programmatically.
- Repack only residues in an approximately 8 Å structural neighborhood.
- Minimize side chains locally while restricting backbone motion to `i-1, i, i+1`.
- Evaluate all 19 substitutions at a selected position.
- Rank mutations by `ΔScore = mutant_score - reference_score`.
- Run an interactive terminal-based human-guided design session.
- Accept or reject proposed mutations without corrupting the accepted state.
- Save mutation history to CSV and JSON.

---

## Current Test System

- **PDB:** 1PGA https://www.rcsb.org/structure/1PGA
- **Length:** 56
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

### Interpretation of ΔScore
- **Negative:** More favorable under the current Rosetta protocol
- **Near zero:** Similar to the reference
- **Positive:** Less favorable

*Small differences should not be overinterpreted.*

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
│       ├── mutation.py
│       ├── scoring.py
│       ├── scan.py
│       └── session.py
├── pyproject.toml
└── README.md
```

### Responsibilities:
- `mutation.py` → residue replacement, local repacking, minimization
- `scoring.py` → score function and Rosetta energy extraction
- `scan.py` → systematic mutation scans
- `session.py` → interactive-session state and history
- `scripts/` → executable workflows

---

## Running

```bash
python scripts/01_load_gb1.py
python scripts/02_mutation_scan.py
python scripts/03_human_guided.py
```

---

## Scientific Design Decisions

### Identical treatment of reference and mutant
Reference and mutant structures are evaluated with the same relaxation protocol before calculating ΔScore.

### Spatial rather than sequence-local repacking
The packing neighborhood is defined in 3D around the mutation. This captures residues that are distant in primary sequence but close in the folded structure.

### Conservative backbone motion
Side chains in the local neighborhood can relax, but backbone motion is limited to residues immediately around the mutation. This reduces the risk that one point mutation causes unrealistic structural remodeling.

### Transparent score decomposition
Individual energy terms are preserved rather than reporting only a single total score.

---

## Example Development Observation

The first E42F experiment illustrates why relaxation matters.

Immediately after direct residue replacement, the mutation produced a very large energetic penalty dominated by steric repulsion. After repacking and minimization, the penalty became much smaller.

This motivated a central V0 rule:
> **Do not interpret the score of an unrelaxed residue replacement as mutation quality.**

---

## Output

Mutation scans are stored under:
```text
data/results/mutation_scans/
```

Human-guided sessions are stored under:
```text
data/results/human_guided_sessions/
```

CSV is intended for analysis and visualization. JSON is intended for structured session persistence and future UI integration.

---

## Environment

V0 was developed with Python 3.11 and a PyRosetta-4 2026 build.

PyRosetta is not bundled with this repository and is subject to Rosetta Commons licensing terms. Users are responsible for complying with the applicable license, including commercial-use requirements.

---

## Known Limitations

V0 is intentionally minimal:
- Only point mutations are supported.
- GB1 is the current benchmark.
- The score is a Rosetta energetic estimate, not experimental ΔΔG.
- Only limited local conformational sampling is performed.
- Packing/minimization may have stochastic components.
- No explicit solvent or molecular dynamics is used.
- No evolutionary or protein-language-model signal is included.
- No automated experimental validation is performed.
- The terminal sequence display is difficult to navigate visually.

The planned UI should therefore include clear residue numbering, mutation highlighting, accepted/proposed states, score-term visualization, history, and ideally a local 3D structural view.
