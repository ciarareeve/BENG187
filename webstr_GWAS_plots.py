from flask import Flask, request, jsonify
import plotly.express as px
import pandas as pd
import numpy as np
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

# Initialize Flask app
server = Flask(__name__)

# Initialize Dash app
app = dash.Dash(__name__, server=server, url_base_pathname='/dash/')

# Placeholder variables for Locus ID and Phenotype
LOCUS_ID = "default_locus"
PHENOTYPE = "default_phenotype"

# Sample locus data function
def generate_locus_data(locus_id, phenotype):
    x = np.linspace(-10, 10, 400)
    y = np.sin(x) + np.random.normal(0, 0.1, len(x))
    df = pd.DataFrame({'Position': x, 'Value': y, 'Locus ID': locus_id, 'Phenotype': phenotype})
    return df

# Define API endpoint to update Locus ID and Phenotype
@server.route("/update_params", methods=["POST"])
def update_params():
    global LOCUS_ID, PHENOTYPE
    data = request.get_json()
    LOCUS_ID = data.get("locus_id", LOCUS_ID)
    PHENOTYPE = data.get("phenotype", PHENOTYPE)
    return jsonify({"message": "Parameters updated", "locus_id": LOCUS_ID, "phenotype": PHENOTYPE})

# Layout for Dash app
app.layout = html.Div([
    html.H1("Locus Advanced Plot"),
    dcc.Graph(id='locus-plot'),
    dcc.Interval(id='interval-update', interval=2000, n_intervals=0)
])

# Callback to update plot
@app.callback(
    Output('locus-plot', 'figure'),
    Input('interval-update', 'n_intervals')
)
def update_plot(n):
    df = generate_locus_data(LOCUS_ID, PHENOTYPE)
    fig = px.line(df, x='Position', y='Value', title=f'Locus Visualization: {LOCUS_ID} ({PHENOTYPE})')
    return fig

if __name__ == "__main__":
    server.run(debug=True)

