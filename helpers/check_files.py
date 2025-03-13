import os

directories = {
    'blessed_set': '/Users/ciarareeve/senior_design/blessed_set',
    'strict_blessed_set': '/Users/ciarareeve/senior_design/strict_blessed_set'
}

file_counts = {}

# Get file counts for each subdirectory in both directories
for label, path in directories.items():
    if os.path.exists(path):
        subdirs = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
        for subdir in subdirs:
            full_subdir_path = os.path.join(path, subdir)
            count = len([f for f in os.listdir(full_subdir_path) if os.path.isfile(os.path.join(full_subdir_path, f))])
            file_counts.setdefault(subdir, {})[label] = count

# Print only if counts don't match
for subdir, counts in file_counts.items():
    if counts.get('blessed_set', 0) != counts.get('strict_blessed_set', 0):
        print(f"""blessed_set/{subdir}
Number of files: {counts.get('blessed_set', 0)}

strict_blessed_set/{subdir}
Number of files: {counts.get('strict_blessed_set', 0)}

""")
