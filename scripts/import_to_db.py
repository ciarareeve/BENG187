#!/usr/bin/env python3
import argparse
import ast
import os
import json
import sqlite3
import polars as pl
import re


def create_db(db_path):
    """
    Create a SQLite database with a table 'locus_data' if it doesn't exist.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS locus_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phenotype TEXT,
            chrom TEXT,
            pos INTEGER,
            data_json TEXT
        );
    """
    )
    conn.commit()
    return conn


def insert_locus_data(conn, phenotype, chrom, pos, data):
    """
    Insert a row into the locus_data table.
    The full row data is stored as a JSON string.
    """
    cur = conn.cursor()
    data_json = json.dumps(data)
    cur.execute(
        """
        INSERT INTO locus_data (phenotype, chrom, pos, data_json)
        VALUES (?, ?, ?, ?)
    """,
        (phenotype, chrom, pos, data_json),
    )
    conn.commit()


def process_file(filepath):
    """
    Reads a .tab file using Polars, extracts the single row (if present),
    and returns a dictionary containing the data.
    """
    try:
        df = pl.read_csv(filepath, separator="\t")
    except Exception as e:
        print(f"[ERROR] Could not read {filepath}: {e}")
        return None

    if df.shape[0] != 1:
        print(f"[WARNING] {filepath} has {df.shape[0]} rows (expected 1); skipping.")
        return None

    row = df.to_dicts()[0]
    chrom = row.get("chrom")
    pos = row.get("pos")
    try:
        pos = int(pos)
    except Exception:
        pos = None

    # You can still extract phenotype from header if needed; here we leave it for later.
    return {"chrom": chrom, "pos": pos, "data": row}


def process_directory(input_dir, conn):
    """
    Recursively process all .tab files in the given directory.
    For files located in a subdirectory, the immediate subdirectory name is used as the phenotype.
    """
    for root, dirs, files in os.walk(input_dir):
        # Use the last part of the current root as the phenotype.
        # (If you want to override this based on header information, you can add that logic.)
        phenotype = os.path.basename(root)
        for file in files:
            if file.endswith(".tab"):
                filepath = os.path.join(root, file)
                result = process_file(filepath)
                if result is None:
                    continue
                insert_locus_data(
                    conn, phenotype, result["chrom"], result["pos"], result["data"]
                )
                print(f"Inserted data from {filepath} under phenotype '{phenotype}'")


def main():
    parser = argparse.ArgumentParser(
        description="Import locus file data into a SQLite database"
    )
    parser.add_argument(
        "--input-path",
        required=True,
        help="Path to a file or directory containing .tab files. Can be a single file, a flat directory, or a directory with subdirectories.",
    )
    parser.add_argument(
        "--db-path",
        required=True,
        help="Path to the SQLite database file to create/use (e.g. /path/to/locus_data.db)",
    )
    args = parser.parse_args()

    conn = create_db(args.db_path)

    if os.path.isfile(args.input_path):
        result = process_file(args.input_path)
        if result:
            # Use file basename (without extension) as phenotype.
            phenotype = os.path.splitext(os.path.basename(args.input_path))[0]
            insert_locus_data(
                conn, phenotype, result["chrom"], result["pos"], result["data"]
            )
            print(f"Inserted data from {args.input_path} under phenotype '{phenotype}'")
    elif os.path.isdir(args.input_path):
        process_directory(args.input_path, conn)
    else:
        print(
            f"[ERROR] The input path {args.input_path} does not exist or is not accessible."
        )

    conn.close()


if __name__ == "__main__":
    main()

