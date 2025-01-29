# import packages
from dash import Dash, html, dash_table, dcc
import pandas as pd
import plotly.express as px
import os

# basic setup, WILL NOT WORK UNTIL YOU GET ACTUAL FILENAMES IN HERE
# idea: read every csv in the data folder but they need to be in one dataframe
df = pd.read_csv(os.path.join(os.path.abspath("."), "data"))
total = str(df["Debit"].sum())
paid = str(df["Credit"].sum())

# initialize the app
app = Dash()

# app layout
app.layout = [
    html.Div(children='Monthly Spending'),
    dash_table.DataTable(data=df.to_dict('records'), page_size=10),
    dcc.Graph(figure=px.pie(df, values='Debit', names='Category')),
    html.Div([dcc.Markdown("# Total Spending: " + total)]),
    html.Div([dcc.Markdown("# Total Paid: " + paid)])
]

# run the app
if __name__ == '__main__':
    app.run(debug=True)
