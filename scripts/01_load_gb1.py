import pyrosetta


PDB_PATH = "../data/raw/1PGA.pdb"


def main():
    pyrosetta.init()

    pose = pyrosetta.pose_from_pdb(PDB_PATH)

    print("Protein loaded successfully!")
    print(f"Number of residues: {pose.total_residue()}")
    print(f"Sequence: {pose.sequence()}")


if __name__ == "__main__":
    main()