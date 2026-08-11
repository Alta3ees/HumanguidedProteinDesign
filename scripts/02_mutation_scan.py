from pathlib import Path

import pandas as pd
import pyrosetta

from human_protein_design.scoring import (
    get_standard_score_function,
    initialize_pyrosetta,
)

from human_protein_design.scan import scan_position
from human_protein_design.mutation import (
    get_spatial_neighbors,
)

PDB_PATH = "data/raw/1PGA.pdb"

POSITION = 42

OUTPUT_DIR = Path(
    "data/results/mutation_scans"
)


def main():

    initialize_pyrosetta()

    pose = pyrosetta.pose_from_pdb(
        PDB_PATH
    )

    score_function = (
        get_standard_score_function()
    )

    wt_aa = pose.residue(POSITION).name1()

    print(
        f"\nScanning position {POSITION} "
        f"({wt_aa})"
    )

    results = scan_position(
        pose,
        position=POSITION,
        score_function=score_function,
    )

    neighbors = get_spatial_neighbors(
    pose,
    center_position=POSITION,
    radius=8.0,
    )

    print(
        f"8 Å neighborhood around position "
        f"{POSITION}:"
    )

    print(neighbors)

    print(
        f"{len(neighbors)} residues selected"
    )
    # Convert results to DataFrame
    df = pd.DataFrame(results)

    # --------------------------------
    # Print ranking
    # --------------------------------

    print("\nMutation ranking")
    print("-" * 45)

    print(
        df[
            [
                "mutation",
                "total_score",
                "delta_score",
            ]
        ].to_string(
            index=False,
            float_format=lambda x: f"{x:.3f}",
        )
    )

    # --------------------------------
    # Save results
    # --------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        OUTPUT_DIR
        / f"1PGA_position_{POSITION}.csv"
    )

    df.to_csv(
        output_path,
        index=False,
    )

    print(
        f"\nResults saved to:"
        f"\n{output_path}"
    )


if __name__ == "__main__":
    main()