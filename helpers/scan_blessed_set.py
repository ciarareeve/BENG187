#!/usr/bin/env python3
import argparse
import os
import shutil
import re
import csv


def normalize_chrom(chrom):
    """
    Normalize chromosome labels so that, for example, "chr3" and "3" match.
    """
    chrom = chrom.strip().lower()
    if chrom.startswith("chr"):
        chrom = chrom[3:]
    return chrom


def parse_query_file(query_path):
    """
    Read the query file and return a list of (chrom, pos) tuples.
    Assumes each line is tab-delimited with at least two columns.
    """
    queries = []
    with open(query_path, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 2:
                continue
            qchrom = normalize_chrom(parts[0])
            try:
                qpos = int(parts[1])
            except ValueError:
                continue
            queries.append((qchrom, qpos))
    return queries


def extract_phenotype(header_keys):
    """
    Look for a header column matching the pattern:
       ^mean_(.+)_per_summed_length$
    If found, return the captured phenotype. If the captured string starts with an extra "mean_",
    drop it. If no such column is found, return "ambiguous".
    """
    pattern = re.compile(r"^mean_(.+)_per_summed_length$")
    for key in header_keys:
        m = pattern.match(key)
        if m:
            pheno = m.group(1)
            # Optionally remove an extra "mean_" prefix if present.
            if pheno.startswith("mean_"):
                pheno = pheno[len("mean_") :]
            return pheno
    return "ambiguous"


def file_matches_query(file_path, query_chrom, query_pos, tolerance):
    """
    Open the file (assumed to be tab-delimited with a header) and check whether:
      - The file's 'chrom' (normalized) matches query_chrom.
      - The file's 'pos' is within tolerance bp of query_pos.
    Returns a tuple (matches, file_chrom, file_pos, header_keys) where:
      - matches is True/False.
      - file_chrom and file_pos are extracted from the file's first row.
      - header_keys is the list of header column names.
    """
    try:
        with open(file_path, "r") as f:
            reader = csv.DictReader(f, delimiter="\t")
            header_keys = reader.fieldnames
            row = next(reader, None)
            if row is None:
                return (False, None, None, header_keys)
            file_chrom = normalize_chrom(row.get("chrom", ""))
            try:
                file_pos = int(row.get("pos", "0"))
            except ValueError:
                return (False, None, None, header_keys)
            if file_chrom == query_chrom and abs(file_pos - query_pos) <= tolerance:
                return (True, file_chrom, file_pos, header_keys)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return (False, None, None, None)


def main():
    parser = argparse.ArgumentParser(
        description="Copy locus files matching query positions with phenotype extraction from header"
    )
    parser.add_argument(
        "--query-file",
        required=True,
        help="Path to the query file (chrom and pos, tab-delimited)",
    )
    parser.add_argument(
        "--source-dir", required=True, help="Directory containing locus files to search"
    )
    parser.add_argument(
        "--output-dir-base",
        required=True,
        help="Base directory where phenotype folders will be created",
    )
    parser.add_argument(
        "--tolerance",
        type=int,
        default=100,
        help="Tolerance (in base pairs) for matching the starting position (default: 100)",
    )

    args = parser.parse_args()

    # Read query positions.
    queries = parse_query_file(args.query_file)
    if not queries:
        print("No valid queries found.")
        return

    # File to store not found queries
    not_found_file = os.path.join(args.output_dir_base, "not_found_queries.txt")
    
    # Open the file in write mode (overwrite if exists)
    with open(not_found_file, "w") as nf:
        nf.write("Phenotype\tChromosome\tPosition\n")  # Add a header

        # Process each query.
        for qchrom, qpos in queries:
            print(f"Processing query: chrom {qchrom}, pos {qpos}")
            match_count = 0

            # Loop over all files in the source directory.
            for fname in os.listdir(args.source_dir):
                fpath = os.path.join(args.source_dir, fname)
                if not os.path.isfile(fpath):
                    continue

                matches, file_chrom, file_pos, header_keys = file_matches_query(
                    fpath, qchrom, qpos, tolerance=args.tolerance
                )
                if not matches:
                    continue

                # Extract phenotype from the file's header.
                phenotype = extract_phenotype(header_keys) if header_keys else "ambiguous"

                # Create the output directory for this phenotype if it doesn't exist.
                out_dir = os.path.join(args.output_dir_base, phenotype)
                os.makedirs(out_dir, exist_ok=True)

                match_count += 1
                # Construct a new file name: {phenotype}_{chrom}_{pos}_{i}{ext}
                _, ext = os.path.splitext(fname)
                new_fname = f"{phenotype}_{file_chrom}_{file_pos}_{match_count}{ext}"
                dest_path = os.path.join(out_dir, new_fname)
                shutil.copy(fpath, dest_path)
                print(f"Copied {fpath} to {dest_path}")

            # If no matches were found, log the missing query
            if match_count == 0:
                phenotype = "unknown"  # Since we can't extract phenotype without finding a file
                nf.write(f"{phenotype}\t{qchrom}\t{qpos}\n")
                print(f"No files found for query: chrom {qchrom}, pos {qpos} (Logged in not_found_queries.txt)")


if __name__ == "__main__":
    main()


"""

python scan_blessed_set.py --query-file /Users/ciarareeve/senior_design/blessed_set/blessed_set.txt --source-dir /Users/ciarareeve/senior_design/dna-nexus-for-locus-plots --output-dir-base /Users/ciarareeve/senior_design/strict_blessed_set --tolerance 5 


"""
