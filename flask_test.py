#!/usr/bin/env python3

from flask import Flask, request, render_template
import json
import os
import csv
from plotly_rewrite import query_allele_data, filter_allele_data, generate_figure_plotly

app = Flask(__name__)

DB_PATH = "/Users/ciarareeve/senior_design/BENG187/locus_data.db"
DUPLICATE_CSV_FILE = "duplicates.csv"

# ============================
# 🚀 FLASK ROUTE
# ============================
@app.route('/test_locus')
def test_locus():
    repeat_id = request.args.get("repeat_id")

    count_threshold = request.args.get("count_threshold", default=100, type=float)
    max_ci_range = request.args.get("max_ci_range", default=None, type=float)
    max_relative_ci_range = request.args.get("max_relative_ci_range", default=None, type=float)

    if not repeat_id:
        return "Error: Missing required parameter 'repeat_id'.", 400

    # Use the existing function from plotly_rewrite.py
    dosage_dict, mean_dict, ci_dict = query_allele_data(DB_PATH, repeat_id)

    if not dosage_dict:
        return f"No GWAS trait association data found for repeat_id {repeat_id}.", 404

    dosage_dict, mean_dict, ci_dict = filter_allele_data(
        dosage_dict, mean_dict, ci_dict, count_threshold, max_ci_range, max_relative_ci_range
    )

    fig = generate_figure_plotly(dosage_dict, mean_dict, ci_dict)

    if fig is None:
        return "Error: Failed to generate plot.", 500

    gwas_plot_json = fig.to_json()

    return render_template("flask_html_test.html", gwas_plot_json=gwas_plot_json, repeat_id=repeat_id)

# ============================
# 🚀 RUN FLASK SERVER
# ============================
if __name__ == '__main__':
    app.run(debug=True)
