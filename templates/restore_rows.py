
import sqlite3
import csv

DB_PATH = "/Users/ciarareeve/senior_design/BENG187/locus_data.db"
REMOVED_ROWS_FILE = "removed_rows.csv"

# Connect to the database
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Get column names from the database
cur.execute("PRAGMA table_info(locus_data);")
columns = [col[1] for col in cur.fetchall()]
num_columns = len(columns)

# Read removed rows from CSV
with open(REMOVED_ROWS_FILE, "r") as f:
    reader = csv.reader(f)
    header = next(reader)  # Skip CSV header
    rows = [tuple(row + [None] * (num_columns - len(row))) for row in reader]  # Fill missing columns

# Generate the correct number of placeholders for SQL query
placeholders = ", ".join(["?"] * num_columns)

# Reinsert data
if rows:
    sql_query = f"INSERT INTO locus_data ({', '.join(columns)}) VALUES ({placeholders})"
    cur.executemany(sql_query, rows)
    conn.commit()
    print(f"✅ Restored {len(rows)} removed rows.")

conn.close()
