"""Test persistence of the v0.3 design archive."""

from pathlib import Path

from human_protein_design.archive import (
    Decision,
    Design,
    DesignArchive,
    EvidenceEntry,
)


OUTPUT_PATH = Path(
    "data/results/test_design_archive.json"
)


archive = DesignArchive()


# --------------------------------------------------
# Root design
# --------------------------------------------------

root = Design(
    sequence="AAAA",
)

archive.add_design(
    root
)


# --------------------------------------------------
# Candidate
# --------------------------------------------------

candidate = Design(
    sequence="AAWA",
    parent_design_id=root.id,
)

archive.add_design(
    candidate
)


# --------------------------------------------------
# Computational evidence
# --------------------------------------------------

evidence = EvidenceEntry(
    source_type="computational",
    source_name="PyRosetta",
    summary="Test mutation evaluation.",
    design_id=candidate.id,
    data={
        "delta_score": 4.2,
    },
)

archive.add_evidence(
    evidence
)


# --------------------------------------------------
# First decision
# --------------------------------------------------

rejection = Decision(
    parent_design_id=root.id,
    candidate_design_id=candidate.id,
    outcome="rejected",
    hypothesis="Improve packing.",
    objective="Improve stability.",
    rationale="Rosetta score worsened.",
)

archive.add_decision(
    rejection
)


# --------------------------------------------------
# Save
# --------------------------------------------------

archive.save(
    OUTPUT_PATH
)

print(
    f"Saved archive to {OUTPUT_PATH}"
)


# --------------------------------------------------
# Reload from disk
# --------------------------------------------------

loaded = DesignArchive.load(
    OUTPUT_PATH
)


print()
print("Archive reloaded successfully.")
print(
    "Designs:",
    len(loaded.designs),
)
print(
    "Decisions:",
    len(loaded.decisions),
)
print(
    "Evidence:",
    len(loaded.evidence),
)


# --------------------------------------------------
# Reconsider rejected candidate
# --------------------------------------------------

new_evidence = EvidenceEntry(
    source_type="experiment",
    source_name="CD",
    summary=(
        "Experimental structure appears stable."
    ),
    design_id=candidate.id,
)

loaded.add_evidence(
    new_evidence
)


acceptance = Decision(
    parent_design_id=root.id,
    candidate_design_id=candidate.id,
    outcome="accepted",
    hypothesis="Improve packing.",
    objective="Improve stability.",
    rationale=(
        "Reconsidered after experimental evidence."
    ),
)

loaded.add_decision(
    acceptance
)


loaded.save(
    OUTPUT_PATH
)


# --------------------------------------------------
# Show decision history
# --------------------------------------------------

print()
print("Decision history:")

for decision in loaded.get_design_decisions(
    candidate.id
):
    print(
        f"  {decision.created_at} "
        f"{decision.outcome.upper()}"
    )


latest = loaded.get_latest_decision(
    candidate.id
)

print()
print(
    "Current decision:",
    latest.outcome
    if latest is not None
    else "none",
)