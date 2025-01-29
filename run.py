# Import packages
from dash import Dash, html, dash_table, dcc, callback, Input, Output
import pandas as pd
import plotly.express as px
import os

# Load all CSV files in 'data' folder
data_path = os.path.join(os.path.abspath("."), "data")
files = [f for f in os.listdir(data_path) if f.endswith('.csv')]

# Read and concatenate all CSV files into one DataFrame
df_list = [pd.read_csv(os.path.join(data_path, file)) for file in files]
df = pd.concat(df_list, ignore_index=True)

# Ensure proper data types
df['Transaction Date'] = pd.to_datetime(df['Transaction Date'])
df['Year'] = df['Transaction Date'].dt.year.astype(str)
df['Month'] = df['Transaction Date'].dt.strftime('%B')

# Get sorted lists for dropdowns
years = sorted(df['Year'].unique(), reverse=True)  # Sort years in descending order
months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

# Remove duplicate transactions
df.drop_duplicates(inplace=True)

# Initialize the app
app = Dash(__name__)

# Define Layout
app.layout = html.Div([
    html.H1("Monthly Spending Dashboard"),
    
    # Year Tabs
    dcc.Tabs(
        id='year-tabs', 
        value=years[0],  # Default to most recent year
        children=[dcc.Tab(label=year, value=year) for year in years]
    ),

    # Month Tabs (Updated Dynamically)
    html.Div(id='month-tabs-container'),

    # Content for selected year and month
    html.Div(id='tab-content')
])

# Update Month Tabs based on Selected Year
@callback(
    Output('month-tabs-container', 'children'),
    [Input('year-tabs', 'value')]
)
def update_month_tabs(selected_year):
    available_months = df[df['Year'] == selected_year]['Month'].unique()
    available_months = sorted(available_months, key=lambda x: months.index(x))  # Sort in calendar order

    return dcc.Tabs(
        id='month-tabs',
        value=available_months[0] if available_months else None,
        children=[dcc.Tab(label=month, value=month) for month in available_months]
    )

# Update Data Table and Pie Chart based on Selected Year & Month
@callback(
    Output('tab-content', 'children'),
    [Input('year-tabs', 'value'),
     Input('month-tabs', 'value')]
)
def update_tab(selected_year, selected_month):
    if not selected_month:
        return html.Div("No transactions available for this selection.")

    # Correct Filtering Syntax
    filtered_df = df[(df['Year'] == selected_year) & (df['Month'] == selected_month)]

    if filtered_df.empty:
        return html.Div("No transactions for this month.")

    # Generate Pie Chart
    pie_chart = px.pie(filtered_df, values='Debit', names='Category', title=f"Spending Breakdown for {selected_month}")

    # Compute Total Spending and Payments
    total_spent = filtered_df["Debit"].sum()
    total_paid = filtered_df["Credit"].sum()

    return html.Div([
        dash_table.DataTable(data=filtered_df.to_dict('records'), page_size=10),
        dcc.Graph(figure=pie_chart),
        html.H3(f"Total Spending: ${total_spent:,.2f}"),
        html.H3(f"Total Paid: ${total_paid:,.2f}")
    ])

# Run the app
if __name__ == '__main__':
    app.run(debug=True)