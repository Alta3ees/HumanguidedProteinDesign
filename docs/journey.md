# Roadmap

## V0 — Completed Core
- Structure loading
- Full-atom scoring
- Point mutation
- Local side-chain repacking
- Conservative local minimization
- ΔScore calculation
- 19-amino-acid position scan
- CSV mutation-scan output
- Human-guided terminal loop
- Accept/reject state handling
- CSV/JSON session persistence

---

## V0.1
- Timestamped session outputs
- Save final accepted PDB
- Reproducibility metadata and random-seed handling
- Automated tests
- Configuration object/file
- Structured logging

---

## V0.2 — UI
- Numbered sequence viewer
- Visible mutation highlighting
- Amino-acid selector
- Accept/reject controls
- Mutation-history panel
- Score-term plots
- 3D structure visualization

---

## Future Scientific Extensions
- Repeated conformational sampling
- Multi-position design
- Experimental benchmark sets
- Stability-focused ΔΔG methods
- Evolutionary conservation
- ProteinMPNN or other sequence-model suggestions
- Multi-objective scoring

---

## Reproducibility
Future releases should record:
- Input structure
- PyRosetta version
- Score function
- Packing radius
- Minimization policy
- Random seed where relevant
- Accepted mutation history
- Final structure

---
---

# Development Journey — Human-Guided Protein Design V0

This document records the scientific and technical path that produced the first working V0 prototype. It is intentionally detailed because many bugs exposed assumptions that matter for reproducibility and future development.

## 1. Starting Point

The initial objective was simple:

Load a protein structure, mutate one residue, score the result with PyRosetta, and progressively turn that into an interactive human-guided design workflow.

**GB1 (1PGA)** was selected as the first benchmark:
- **Residues:** 56
- **Sequence:** `MTYKLILNGKTLKGETTTEAVDAATAEKVFKQYANDNGVDGEWTYDDATKTFTVTE`

The intended long-term loop was:

```text
Human proposes mutation
         ↓
Structure is evaluated
         ↓
Human receives feedback
         ↓
Human accepts/rejects
         ↓
Repeat
```

Before building a UI, the structural evaluation had to be made reliable.

---

## 2. Structure Loading

PyRosetta initialization and PDB loading worked successfully. The pose reported 56 residues and the expected GB1 sequence.

This established that the input PDB, Rosetta database, and base environment were functioning.

---

## 3. First Scoring Implementation

The first scoring implementation used:
```python
score_string = str(score_function.show(pose))
```
and attempted to parse the displayed score breakdown.

This was fragile because `show()` is meant for human-readable reporting rather than structured data extraction.

The implementation was replaced with Rosetta's pose-energy map:
```python
pose.energies().total_energies()
```
combined with the score-function weights.

> **Lesson:** Prefer structured scientific APIs over parsing display text.

---

## 4. Native Segmentation Fault

The first major blocker was:
```text
Fatal Python error: Segmentation fault
```

Initially the crash appeared related to scoring because only the total score had been printed.

Running:
```bash
python -X faulthandler scripts/01_load_gb1.py
```
identified the true failure site: `mutation.py` → `mutate_pose()`, specifically:
```python
MutateResidue(position, mutant_aa).apply(mutant_pose)
```

A minimal isolated test reproduced the crash directly inside `MutateResidue.apply()`. That isolated reproduction showed the problem was not caused by the project architecture, score extraction, or PDB loading.

The development environment used a PyRosetta-4 2026.30 build with Python 3.11.

> **Decision:** The project stopped using that mover and implemented mutation through lower-level pose/residue APIs.

---

## 5. Reimplementing Mutation

The replacement strategy uses:

```text
One-letter amino-acid code
           ↓
Three-letter Rosetta residue name
           ↓
fa_standard ResidueType
           ↓
ResidueFactory
           ↓
Pose.replace_residue()
```

An early attempt incorrectly called:
```python
pose.residue_type(42).residue_type_set()
```
and raised:
```text
AttributeError: 'ResidueType' object has no attribute 'residue_type_set'
```

The corrected implementation obtained `fa_standard` through Rosetta's `ChemicalManager`. The isolated replacement test then worked without a native crash.

---

## 6. Residue-Numbering Mistake

The mutation under test had been labeled `L42F`.

However:
```python
pose.residue(42).name1()
```
returned `E`. The actual mutation was therefore `E42F`.

> **Lesson:** Always verify numbering and WT residue identity against the actual Rosetta pose. Structural-biology numbering can differ because of constructs, missing residues, insertion codes, tags, or PDB numbering conventions.

---

## 7. Unrelaxed E42F Looked Catastrophic

Immediately after direct residue replacement, an early result was approximately:
- **WT total score:** -19.207
- **E42F total score:** +29.181
- **ΔScore:** +48.388 REU

The largest deterioration came from steric repulsion (`fa_rep`).

This was not yet a meaningful mutation-quality estimate because phenylalanine had been inserted into geometry that had been arranged for glutamate.

The structure needed to relax.

---

## 8. Side-Chain Repacking

A Rosetta packing stage was added while explicitly restricting the task to repacking rather than sequence design.

Initially the whole protein was repacked. Steric repulsion dropped only modestly, roughly from ~75 to ~72 in the test.

That indicated that rotamer optimization alone could not fully relieve the strain.

---

## 9. Local Minimization

A `MoveMap` and `MinMover` were added.

Once both reference and mutant received repacking and minimization, E42F changed dramatically. One test produced approximately:
- **WT:** -92.968
- **E42F:** -91.966
- **ΔScore:** +1.002 REU

The enormous raw penalty had largely been caused by an unrelaxed structural clash.

> **Major V0 lesson:** Never interpret the score immediately after direct residue replacement as the mutation's energetic effect.

---

## 10. Fair Reference-vs-Mutant Treatment

A second scientific correction was required: reference and mutant must receive the same relaxation protocol.

The standardized comparison became:

```text
Reference → Repack → Minimize → Score
Mutant    → Repack → Minimize → Score

ΔScore = mutant - reference
```

This principle is retained throughout V0.

---

## 11. Mutation Iteration

After one mutation worked, the next step was systematic scanning.

A reusable `scan_position()` workflow was introduced to evaluate all 19 alternatives at one residue, calculate ΔScores, rank the substitutions, and retain individual score terms.

This moved the project from a one-off PyRosetta experiment toward reusable software.

---

## 12. Structured Results

Mutation scans were exported to CSV.

The project output hierarchy was reorganized from a separate top-level `results/` directory into:
```text
data/
├── raw/
└── results/
```
This cleanly separates inputs from generated results.

The mutation-scan table retains residue identity, mutation, total score, selected Rosetta terms, and ΔScore.

---

## 13. Spatial Neighborhoods

The first local relaxation implementation used a sequence window such as position ± 4. That is convenient but structurally naive.

Proteins fold in three dimensions, so residues far apart in sequence can be direct spatial neighbors.

The protocol was changed to use an approximately 8 Å spatial neighborhood. For residue 42, one observed neighborhood was:
```text
[41, 42, 43, 44, 54, 55, 56]
```
The presence of residues 54–56 validated the basic idea: they are far from 42 in primary sequence but close in the folded structure.

> **Lesson:** For structural mutation evaluation, spatial locality is more meaningful than sequence locality.

---

## 14. Restricting Backbone Freedom

The first spatial implementation allowed backbone motion for all residues in the 8 Å neighborhood.

This was considered too permissive for a point-mutation evaluation. The V0 protocol was tightened to:
- **Side-chain χ:** residues within ~8 Å
- **Backbone φ/ψ:** i-1, i, i+1 only
- **Jumps:** frozen

This keeps enough flexibility to resolve local strain without allowing one mutation to cause large local remodeling.

---

## 15. Repeated Relaxation Messages

A temporary diagnostic printed:
```text
Local relaxation around 42:
7 side-chain residues, backbone 41-43
```

During a 19-amino-acid scan the line appeared many times. This was normal because relaxation was executed once for the reference and once for each mutant.

The noisy low-level print was removed after the neighborhood was validated.

---

## 16. Python Package Initialization Bug

The package initialization file was initially misnamed `_init__.py` instead of `__init__.py`.

Correcting the filename helped resolve the project/import configuration issue involving `pyproject.toml`.

---

## 17. Human-Guided Session Layer

With the structural engine sufficiently stable for V0, a session abstraction was introduced.

The key architectural separation is:
- `evaluate_mutation(...)` vs. `accept_mutation(...)`

Evaluation creates and scores a temporary proposal. Acceptance alone updates the persistent current structure.

This guarantees that rejected mutations do not alter the accepted design state.

Conceptually:

```text
Accepted pose
      ↓
Propose mutation
      ↓
Temporary evaluation
      ↓
Show feedback
     ↙   ↘
Reject   Accept
   ↓       ↓
Discard  Update current pose
```

---

## 18. No-Op Mutation Bug

During terminal testing, a mutation such as M → M was attempted.

Unexpectedly, the score changed on the first attempt. The explanation was that the pipeline still performed repacking and minimization even though the sequence identity had not changed. That could move the pose into a different local minimum.

Repeating the same no-op then gave approximately zero ΔScore because the structure was already close to that relaxed state.

> **Fix:** No-op mutations are now rejected before structural evaluation. A future UI should simply disable the currently selected amino acid.

---

## 19. Session-Persistence Bug

CSV and JSON session saving was added.

The first quit attempt raised:
```text
NameError: OUTPUT_DIR is not defined
```

The output-saving code had been added without defining its path constant. Defining:
```python
OUTPUT_DIR = Path("data/results/human_guided_sessions")
```
resolved the issue.

---

## 20. Terminal UX Limitation

The terminal loop works, but a major usability problem became obvious: a raw sequence string is difficult to navigate.

For example:
```text
MTYKLILNGKTLKGETTTEAVDAATAEKVFKQYANDNGVDGEWTYDDATKTFTVTE
```
does not make it easy to locate residue i, identify what changed, or track several accepted mutations.

This directly defines requirements for the future UI:
- Residue numbering
- Sequence blocks
- Mutation highlighting
- Clear current/proposed/accepted states
- Mutation-history display
- Score-term visualization
- Local structural context

For a human-guided scientific tool, readability is part of the scientific workflow rather than merely a cosmetic concern.

---

## 21. V0 Software Architecture

```text
data/
├── raw/
└── results/
    ├── mutation_scans/
    └── human_guided_sessions/

scripts/
├── 01_load_gb1.py
├── 02_mutation_scan.py
└── 03_human_guided.py

src/human_protein_design/
├── __init__.py
├── mutation.py
├── scoring.py
├── scan.py
└── session.py
```

### Responsibilities:
- `mutation.py`: residue replacement, spatial neighbor selection, local repacking, minimization
- `scoring.py`: PyRosetta initialization, score function, weighted energy terms
- `scan.py`: systematic substitution scans
- `session.py`: proposal evaluation, accepted state, mutation history, persistence
- `scripts/`: user-facing executable workflows

---

## 22. Frozen V0 Structural Protocol

The V0 evaluation path is:

```text
Input pose
    ↓
Select position i
    ↓
Replace residue
    ↓
Find ~8 Å neighborhood
    ↓
Repack local side chains
    ↓
Minimize local χ angles
    ↓
Minimize backbone only at i-1 / i / i+1
    ↓
Calculate Rosetta terms
    ↓
Compare with identically treated reference
    ↓
Report ΔScore
```

This protocol is intentionally frozen for the first release so that development can move toward usability, testing, and reproducibility instead of continually changing the scientific baseline.

---

## 23. Scientific Caveats

The V0 score is not an experimental stability measurement. In particular:
- Rosetta energy units are model-dependent.
- One local minimum does not represent a conformational ensemble.
- Packing can contain stochasticity.
- Solvent is implicit.
- Entropy is incompletely represented.
- Evolutionary constraints are absent.
- Functional effects are not directly assessed.

Therefore, a negative ΔScore means **more favorable under this V0 Rosetta protocol**, not *experimentally proven to improve the protein*.

---

## 24. Why V0 Matters

Despite those limitations, V0 establishes the complete minimal human-in-the-loop architecture:
- A human can propose mutations.
- Structural context is considered.
- Reference and mutant receive the same treatment.
- Energetic components are visible.
- Accepted mutations persist.
- Rejected mutations do not alter state.
- Scan/session data are structured.
- The design can continue iteratively.

The project has therefore evolved from a PyRosetta mutation experiment into a minimal human-guided protein-design system.

---

## 25. Next Priorities

### Release/Reproducibility
- Timestamp session outputs
- Save final accepted PDB
- Record PyRosetta version and protocol configuration
- Expose random-seed controls where possible
- Add automated tests
- Add structured logging

### Human-Guided UI
- Numbered sequence viewer
- Strong mutation highlighting
- Current/proposed/accepted visual states
- Amino-acid selector
- Accept/reject controls
- History panel
- Score-term plots
- Local 3D structure view

### Scientific Validation
- Benchmark against mutations with known experimental effects
- Repeat packing/minimization to characterize run-to-run variability
- Test sensitivity to spatial radius
- Compare with established stability/ΔΔG workflows

---

## 26. Core Lessons

1. Isolate native crashes before redesigning the application.
2. Prefer structured scientific APIs over parsing display output.
3. Verify residue identity and numbering directly from the pose.
4. Do not interpret unrelaxed substitution scores.
5. Treat reference and mutant structures identically.
6. Use 3D structural neighborhoods rather than only sequence distance.
7. Restrict structural freedom to match the scientific question.
8. Separate mutation evaluation from mutation acceptance.
9. Explicitly reject no-op mutations.
10. A human-guided scientific interface must make sequence position and structural change easy to interpret.

---

## 27. V0 Milestone

By the end of this development cycle the project supports:
- PyRosetta structure loading
- Robust point mutation generation
- Structured Rosetta score extraction
- Local side-chain repacking
- Conservative local minimization
- 19-amino-acid mutation scanning
- CSV scan output
- Iterative human decisions
- Accepted-state tracking
- CSV/JSON session persistence

That constitutes the first coherent V0 of **Human-Guided Protein Design**.
