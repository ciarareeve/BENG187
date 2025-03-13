#!/usr/bin/env python3
import argparse
import ast
import os
import polars as pl
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.ticker import MultipleLocator, MaxNLocator
import numpy as np
import math
import shutil


def parse_float_or_nan(x):
    """
    If x is a string that says 'NaN', return float('nan').
    Otherwise, try to cast x to float.
    """
    if isinstance(x, str):
        if x.lower() == "nan":
            return float("nan")
        else:
            return float(x)
    return float(x)


def filter_allele_data(
    dosage_dict,
    mean_dict,
    ci_dict,
    count_threshold=100,
    lower_threshold=None,
    upper_threshold=None,
    max_ci_range=None,
    max_relative_ci_range=None,
):
    """
    Filter allele data based on a sample count threshold and optionally
    on confidence interval (CI) criteria.
    """
    filtered_dosage = {}
    filtered_mean = {}
    filtered_ci = {}

    for allele in dosage_dict.keys():
        # Check count threshold first.
        count_val = parse_float_or_nan(dosage_dict[allele])
        if count_val < count_threshold:
            continue

        # Parse CI values and mean.
        try:
            lower = parse_float_or_nan(ci_dict[allele][0])
            upper = parse_float_or_nan(ci_dict[allele][1])
        except (IndexError, TypeError, ValueError):
            continue

        mean_val = parse_float_or_nan(mean_dict[allele])

        # Exclude data with NaNs.
        if np.isnan(lower) or np.isnan(upper) or np.isnan(mean_val):
            continue

        # Optionally, apply CI bounds filtering.
        if lower_threshold is not None and lower < lower_threshold:
            continue
        if upper_threshold is not None and upper > upper_threshold:
            continue

        # Optionally, filter out alleles with too wide an absolute CI.
        if max_ci_range is not None and (upper - lower) > max_ci_range:
            continue

        # Optionally, filter out alleles with too wide a CI relative to the mean.
        if max_relative_ci_range is not None:
            relative_ci = (upper - lower) / mean_val
            if relative_ci > max_relative_ci_range:
                continue

        # If all checks pass, keep the allele.
        filtered_dosage[allele] = dosage_dict[allele]
        filtered_mean[allele] = mean_dict[allele]
        filtered_ci[allele] = ci_dict[allele]

    return filtered_dosage, filtered_mean, filtered_ci


def generate_figure_matplotlib(
    dosage_dict,
    mean_dict,
    ci_dict,
    phenotype,
    unit=None,
    bw=False,
    user_x_min=None,
    user_x_max=None,
    user_y_min=None,
    user_y_max=None,
):
    # Set up the y-axis label.
    y_axis_label = phenotype.replace("_", " ")
    if unit:
        y_axis_label += f" ({unit})"
    y_axis_label = y_axis_label[0].upper() + y_axis_label[1:]

    fig, ax = plt.subplots(figsize=(10, 8))

    # Sort alleles numerically.
    sorted_alleles_str = sorted(dosage_dict.keys(), key=float)
    if not sorted_alleles_str:
        ax.set_xlabel("Sum of allele lengths (repeat copies)", fontsize=16)
        ax.set_ylabel(y_axis_label, fontsize=16)
        return fig, ax

    # Convert allele strings to float values for plotting.
    sorted_alleles = [float(a) for a in sorted_alleles_str]

    # Build numeric arrays from the filtered dictionaries.
    ci_lower = [parse_float_or_nan(ci_dict[a][0]) for a in sorted_alleles_str]
    ci_upper = [parse_float_or_nan(ci_dict[a][1]) for a in sorted_alleles_str]
    mean_vals = [parse_float_or_nan(mean_dict[a]) for a in sorted_alleles_str]

    # Create the plot.
    if not bw:
        ax.fill_between(
            sorted_alleles, ci_lower, ci_upper, color="red", alpha=0.3, label="95% CI"
        )
        ax.plot(sorted_alleles, mean_vals, linewidth=3, color="black", label="Mean")
        ax.scatter(sorted_alleles, mean_vals, marker="o", color="black", s=64)
    else:
        lower_errors = [mean_vals[i] - ci_lower[i] for i in range(len(sorted_alleles))]
        upper_errors = [ci_upper[i] - mean_vals[i] for i in range(len(sorted_alleles))]
        y_err = np.array([lower_errors, upper_errors])
        ax.errorbar(
            sorted_alleles,
            mean_vals,
            yerr=y_err,
            fmt="o-",
            color="black",
            ecolor="black",
            elinewidth=1,
            capsize=3,
            label="95% CI",
        )

    ax.set_xlabel("Sum of allele lengths (repeat copies)", fontsize=16)
    ax.set_ylabel(y_axis_label, fontsize=16)
    ax.legend(fontsize=12, loc="best")

    # X-axis: ticks and limits.
    if user_x_min is not None and user_x_max is not None:
        ax.set_xlim(user_x_min, user_x_max)
        ax.xaxis.set_major_locator(MultipleLocator(5))
    else:
        ax.xaxis.set_major_locator(MaxNLocator(nbins=6, integer=True))

    # Y-axis: ticks and limits.
    if user_y_min is not None and user_y_max is not None:
        ax.set_ylim(user_y_min, user_y_max)
        ax.yaxis.set_major_locator(MultipleLocator(5))
    else:
        auto_y_min = min(ci_lower)
        auto_y_max = max(ci_upper)
        margin = 0.05 * (auto_y_max - auto_y_min)
        ax.set_ylim(auto_y_min - margin, auto_y_max + margin)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=6, integer=True))

    return fig, ax


def process_files(file_paths, phenotype, args):
    output_phenotype_dir = os.path.join(args.output_dir, phenotype)
    os.makedirs(output_phenotype_dir, exist_ok=True)
    file_counter = 0

    for filepath in file_paths:
        try:
            df = pl.read_csv(filepath, separator="\t")
        except Exception as e:
            print(f"[ERROR] Could not read {filepath}: {e}")
            continue

        if df.shape[0] != 1:
            print(f"[WARNING] Found {df.shape[0]} rows in {filepath}, skipping...")
            continue

        row = df.to_dicts()[0]
        chrom = row["chrom"]
        pos = row["pos"]

        # Get dictionaries.
        dosage_dict = ast.literal_eval(row[args.total_column_name])
        candidate_mean_cols = [c for c in row.keys() if c.startswith("mean_")]
        if len(candidate_mean_cols) != 1:
            print(
                f"[WARNING] Could not find exactly 1 column starting with 'mean_' in {filepath}, skipping..."
            )
            continue
        mean_col_name = candidate_mean_cols[0]
        mean_dict = ast.literal_eval(row[mean_col_name])
        ci_dict = ast.literal_eval(row["summed_length_0.05_alpha_CI"])

        # Filter allele data.
        dosage_dict, mean_dict, ci_dict = filter_allele_data(
            dosage_dict,
            mean_dict,
            ci_dict,
            count_threshold=args.count_threshold,
            lower_threshold=None,  # or set a value
            upper_threshold=None,  # or set a value
            max_ci_range=args.max_ci_range,
            max_relative_ci_range=args.max_relative_ci_range,
        )

        # Generate the figure.
        fig, ax = generate_figure_matplotlib(
            dosage_dict,
            mean_dict,
            ci_dict,
            phenotype,
            unit=args.unit,
            bw=args.bw,
            user_x_min=args.x_min,
            user_x_max=args.x_max,
            user_y_min=args.y_min,
            user_y_max=args.y_max,
        )

        # Construct output filename: {phenotype}_{chrom}_{pos}_{i}.png
        output_fname = f"{phenotype}_{chrom}_{pos}_{file_counter}.png"
        output_path = os.path.join(output_phenotype_dir, output_fname)
        fig.savefig(output_path)
        print(f"Saved plot to {output_path}")
        plt.close(fig)

        file_counter += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-path",
        required=True,
        help="Path to a file or directory containing .tab files. If a directory, can be flat or contain phenotype subdirectories.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Base directory where figures will be saved. Output will be saved under {output-dir}/{phenotype}",
    )
    parser.add_argument(
        "--total-column-name",
        required=True,
        help="Column holding a JSON dict of sample counts (e.g. sample_count_per_summed_length)",
    )
    parser.add_argument(
        "--unit", default=None, help="Optional y-axis unit label (e.g., 10^9 cells/L)"
    )
    parser.add_argument(
        "--bw",
        action="store_true",
        default=False,
        help="If set, produce black-and-white whisker plot instead of red fill shading.",
    )
    parser.add_argument(
        "--count-threshold",
        type=float,
        default=100,
        help="Skip alleles whose count is below this threshold (default=100).",
    )
    parser.add_argument(
        "--max-ci-range",
        type=float,
        default=None,
        help="Skip any allele whose absolute CI range (CI_upper - CI_lower) exceeds this.",
    )
    parser.add_argument(
        "--max-relative-ci-range",
        type=float,
        default=None,
        help="Skip any allele whose relative CI range ((CI_upper - CI_lower)/mean) exceeds this value.",
    )
    # Arguments for manual x/y axis.
    parser.add_argument(
        "--x-min", type=float, default=None, help="Manual left limit for x-axis"
    )
    parser.add_argument(
        "--x-max", type=float, default=None, help="Manual right limit for x-axis"
    )
    parser.add_argument(
        "--y-min", type=float, default=None, help="Manual bottom limit for y-axis"
    )
    parser.add_argument(
        "--y-max", type=float, default=None, help="Manual top limit for y-axis"
    )

    args = parser.parse_args()

    input_path = args.input_path
    files_to_process = []

    if os.path.isfile(input_path):
        # Single file option
        files_to_process = [input_path]
        # Use file basename as phenotype
        phenotype = os.path.splitext(os.path.basename(input_path))[0]
        process_files(files_to_process, phenotype, args)
    elif os.path.isdir(input_path):
        # Check if the directory has subdirectories
        subdirs = [
            d
            for d in os.listdir(input_path)
            if os.path.isdir(os.path.join(input_path, d))
        ]
        if subdirs:
            # Loop over each subdirectory.
            for subdir in subdirs:
                subdir_path = os.path.join(input_path, subdir)
                # Gather all .tab files in this subdirectory.
                files = [
                    os.path.join(subdir_path, f)
                    for f in os.listdir(subdir_path)
                    if f.endswith(".tab")
                ]
                if files:
                    process_files(files, subdir, args)
                else:
                    print(f"[INFO] No .tab files found in {subdir_path}")
        else:
            # No subdirectories: assume the directory itself contains the .tab files.
            files = [
                os.path.join(input_path, f)
                for f in os.listdir(input_path)
                if f.endswith(".tab")
            ]
            # Use the directory name as the phenotype.
            phenotype = os.path.basename(os.path.normpath(input_path))
            if files:
                process_files(files, phenotype, args)
            else:
                print(f"[INFO] No .tab files found in {input_path}")
    else:
        print(
            f"[ERROR] The input path {input_path} does not exist or is not accessible."
        )


if __name__ == "__main__":
    main()



