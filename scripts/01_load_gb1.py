import pyrosetta

from human_protein_design.scoring import (
    get_score_terms,
    get_standard_score_function,
    initialize_pyrosetta,
)

from human_protein_design.mutation import (
    mutate_pose,
    repack_pose,
    minimize_local_pose,
)

PDB_PATH = "data/raw/1PGA.pdb"


def print_score_table(label: str, scores: dict[str, float]) -> None:
    """Print score terms in a formatted table."""

    print(f"\n{label}")
    print("-" * 38)
    print(f"{'Term':<20} {'Score':>12}")
    print("-" * 38)

    for name, value in scores.items():
        print(f"{name:<20} {value:>12.3f}")

    print("-" * 38)


def main():
    initialize_pyrosetta()

    pose = pyrosetta.pose_from_pdb(PDB_PATH)

    print("Protein loaded successfully!")
    print(f"Number of residues: {pose.total_residue()}")
    print(f"Sequence: {pose.sequence()}")

    score_function = get_standard_score_function()

    # -------------------------           
    # WT            
    # -------------------------         

    wt_pose = repack_pose(          
        pose,           
        score_function,         
    )           

    wt_pose = minimize_local_pose(          
        wt_pose,            
        score_function,         
        center_position=42,         
    )           

    wt_scores = get_score_terms(            
        wt_pose,            
        score_function,         
    )           

    print_score_table(          
        "WT — repacked + minimized",            
        wt_scores,          
    )           


    # -------------------------         
    # E42F mutant           
    # -------------------------         

    mutant_pose = mutate_pose(          
        pose,           
        position=42,            
        mutant_aa="F",          
    )           

    mutant_pose = repack_pose(          
        mutant_pose,            
        score_function,         
    )           

    mutant_pose = minimize_local_pose(          
        mutant_pose,            
        score_function,         
        center_position=42,         
    )           

    mutant_scores = get_score_terms(            
        mutant_pose,            
        score_function,         
    )           

    print_score_table(          
        "E42F — repacked + minimized",          
        mutant_scores,          
    )           


    # -------------------------         
    # Delta score           
    # -------------------------         

    delta_score = (         
        mutant_scores["total_score"]            
        - wt_scores["total_score"]          
    )           
        
    print(f"\nΔScore E42F - WT: {delta_score:.3f} REU") 
if __name__ == "__main__":          
    main()