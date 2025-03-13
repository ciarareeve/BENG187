import sqlite3
import csv

# Paths
DB_PATH = "/Users/ciarareeve/senior_design/BENG187/locus_data.db"
CSV_FILE = "output_repeat_ids.csv"

# Connect to the database
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Ensure the repeat_id column exists
cur.execute("PRAGMA table_info(locus_data);")
columns = [col[1] for col in cur.fetchall()]
if "repeat_id" not in columns:
    cur.execute("ALTER TABLE locus_data ADD COLUMN repeat_id TEXT;")
    conn.commit()
    print("✅ Added 'repeat_id' column to locus_data.")

# Load repeat_id mappings from CSV into a dictionary
repeat_id_map = {}
with open(CSV_FILE, "r") as f:
    reader = csv.reader(f)
    header = next(reader)  # Skip header
    for row in reader:
        repeat_id, chrom, start, _ = row  # Ignore 'end' column
        formatted_chrom = f"chr{chrom}"  # Ensure it matches DB format
        try:
            repeat_id_map[(formatted_chrom, int(start))] = repeat_id
        except ValueError:
            print(f"Skipping invalid row: {row}")  # Handle bad data

# Update database with repeat_id where chrom and pos match
updated_count = 0
cur.execute("SELECT id, chrom, pos FROM locus_data WHERE repeat_id IS NULL OR repeat_id = ''")
rows = cur.fetchall()

for row in rows:
    db_id, db_chrom, db_pos = row
    key = (db_chrom, db_pos)

    if key in repeat_id_map:
        repeat_id = repeat_id_map[key]
        cur.execute("UPDATE locus_data SET repeat_id = ? WHERE id = ?", (repeat_id, db_id))
        updated_count += 1

conn.commit()
conn.close()

print(f"✅ Updated {updated_count} entries with repeat_id.")
