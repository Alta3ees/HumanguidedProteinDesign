# Human-Guided Protein Design
One mutation at a time, which path would you choose for your protein design?

An open-source research project exploring whether humans can learn to navigate
local protein fitness landscapes through sequential mutation and structural
feedback.

## Idea

Starting from a known protein sequence and structure, a participant introduces
one amino-acid mutation at a time.

After each mutation, computational protein-design methods evaluate the resulting
structure. The participant receives feedback and chooses the next mutation.

The long-term goal is to investigate whether humans can learn useful protein
design strategies through iterative interaction with computational models.

```text
        Starting protein
               │
               ▼
        Human chooses
          one mutation
               │
               ▼
       Computational
          evaluation
               │
               ▼
        Feedback to human
               │
               ▼
        Next mutation
               │
               └──────────────► ...
