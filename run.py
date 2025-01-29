# Import packages
from dash import Dash, html, dash_table, dcc
import pandas as pd
import plotly.express as px
import os

# basic setup
filename = input("Enter the name of the file to load in: ")
df = pd.read_csv(os.path.join(os.path.abspath("."), "data", filename))
total = str(df["Debit"].sum())
paid = str(df["Credit"].sum())

# Initialize the app
app = Dash()

# App layout
app.layout = [
    html.Div(children='Monthly Spending'),
    dash_table.DataTable(data=df.to_dict('records'), page_size=10),
    dcc.Graph(figure=px.pie(df, values='Debit', names='Category')),
    html.Div([dcc.Markdown("# Total Spending: " + total)]),
    html.Div([dcc.Markdown("# Total Paid: " + paid)])
]

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
