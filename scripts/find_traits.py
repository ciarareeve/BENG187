import argparse
import os
import polars as pl
import shutil


def find_files_with_trait(
    directory, chrom=None, pos=None, trait=None, motif=None, margin=20
):
    matching_files = []

    # Loop through all files in the directory
    for filename in os.listdir(directory):
        if filename.endswith(".tab"):
            file_path = os.path.join(directory, filename)

            try:
                # Read in the file
                df = pl.read_csv(file_path, separator="\t", n_rows=1)
                cols = df.columns

                # Check for matching chrom
                chrom_match = chrom is None or (
                    "chrom" in df.columns and df["chrom"][0] == chrom
                )

                # Check for matching pos with margin
                if pos is not None and "pos" in df.columns:
                    file_pos = df["pos"][0]
                    pos_match = pos - margin <= file_pos <= pos + margin
                else:
                    pos_match = (
                        pos is None
                    )  # If pos is not provided, match is True by default

                # Check for the trait in the column names
                trait_match = trait is None or any(
                    trait.lower() in col.lower() for col in cols
                )

                # Check for the motif match if a "motif" column exists
                if motif is not None and "motif" in df.columns:
                    motif_match = df["motif"][0] == motif
                else:
                    motif_match = (
                        motif is None
                    )  # If motif is not provided, match is True by default

                # Append to matching files if all conditions are met
                if chrom_match and pos_match and trait_match and motif_match:
                    matching_files.append(
                        (filename, len(cols))
                    )  # Store filename and column count

            except Exception as e:
                print(f"Error reading {filename}: {e}")

    return matching_files


def copy_files_to_directory(files, source_directory, target_directory):
    """Copy the matching files to a new directory."""
    if not os.path.exists(target_directory):
        os.makedirs(target_directory)

    for filename, _ in files:
        source_path = os.path.join(source_directory, filename)
        destination_path = os.path.join(target_directory, filename)

        shutil.copy(source_path, destination_path)
        print(f"Copied {filename} to {target_directory}")


def main():
    parser = argparse.ArgumentParser(
        description="Find files with specific criteria and copy them."
    )
    parser.add_argument(
        "--directory", required=True, help="Path to the dna nexus directory"
    )
    parser.add_argument("--chrom", help="Chromosome to search for")
    parser.add_argument("--pos", type=int, help="Position to search for")
    parser.add_argument("--trait", help="Trait to search for (partial match)")
    parser.add_argument("--motif", help="Motif to search for in the 'motif' column")
    parser.add_argument("--new-dir", help="New directory to copy matching files into")
    parser.add_argument(
        "--margin",
        type=int,
        default=20,
        help="Margin for position matching (default: 20)",
    )
    args = parser.parse_args()

    # Find matching files
    matching_files = find_files_with_trait(
        args.directory, args.chrom, args.pos, args.trait, args.motif, args.margin
    )

    # Print the results
    if matching_files:
        print(f"Found {len(matching_files)} file(s) matching the given criteria:")
        for filename, col_count in matching_files:
            print(f"{filename} (Columns: {col_count})")

        # If new-dir flag is provided, copy files
        if args.new_dir:
            copy_files_to_directory(matching_files, args.directory, args.new_dir)
    else:
        print(f"No files found matching the given criteria.")


if __name__ == "__main__":
    main()
