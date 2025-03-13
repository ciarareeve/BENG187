import re
import csv
from bs4 import BeautifulSoup

# File paths
INPUT_HTML = "/Users/ciarareeve/senior_design/helpers/gwas_hg38.html"  # Replace with actual HTML file path
OUTPUT_CSV = "output_repeat_ids.csv"

# Read the HTML file
with open(INPUT_HTML, "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

# Find all <a> tags with href containing repeat_id and hg38
rows = []
for link in soup.find_all("a", href=True):
    href = link["href"]
    text = link.get_text(strip=True)  # Extract visible text (e.g., "10:44390336-44390351")

    # Match only hg38 links with repeat_id
    match = re.search(r"repeat_id=(\d+)&genome=hg38", href)
    if match:
        repeat_id = match.group(1)
        
        # Ensure the text follows the expected chrom:start-end format
        coord_match = re.match(r"(\d+|X|Y):(\d+)-(\d+)", text)
        if coord_match:
            chrom, start, end = coord_match.groups()
            rows.append([repeat_id, chrom, start, end])

# Save to CSV
with open(OUTPUT_CSV, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["repeat_id", "chrom", "start", "end"])
    writer.writerows(rows)

print(f"Extracted {len(rows)} entries and saved to {OUTPUT_CSV}")
