# Import packages
from dash import Dash, html, dash_table, dcc, callback, Input, Output
import pandas as pd
import plotly.express as px
import os
from data_loader import load_all_transactions, categorize_transactions, load_category_keywords

# Load, normalize, and categorize all CSV files in 'data' folder.
# categorize_transactions assigns 'Custom Category' and drops payments/income/transfers.
data_path = os.path.join(os.path.abspath("."), "data")
df = categorize_transactions(load_all_transactions(data_path))

# Ensure proper data types
df['Transaction Date'] = pd.to_datetime(df['Transaction Date'])
df['Year'] = df['Transaction Date'].dt.year.astype(str)
df['Month'] = df['Transaction Date'].dt.strftime('%B')

# Get sorted lists for dropdowns
years = sorted(df['Year'].unique(), reverse=True)  # Sort years in descending order
months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

# Remove duplicate transactions
df.drop_duplicates(inplace=True)

# Fixed color per category so a category keeps the same color across every
# monthly tab. Assigned in sorted (deterministic) order — the first eight hues
# are the validated dark-mode categorical slots; 'Unknown' is pinned to gray.
_, category_names = load_category_keywords()
CATEGORY_PALETTE = [
    "#3987e5", "#199e70", "#c98500", "#008300", "#9085e9", "#e66767",
    "#d55181", "#d95926", "#22c1d6", "#a0d33c", "#f48fb1", "#b968e0",
    "#ffca28", "#b08968", "#6d8fd4", "#e0a94b",
]
CATEGORY_COLORS = {
    name: CATEGORY_PALETTE[i % len(CATEGORY_PALETTE)]
    for i, name in enumerate(sorted(category_names))
}
CATEGORY_COLORS["Unknown"] = "#7f8c8d"

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
        value=available_months[-1] if available_months else None,  # default to most recent month with data
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

    # Generate Pie Chart (dark styled). color + color_discrete_map pins each
    # category to a fixed color so it's consistent across monthly tabs.
    pie_chart = px.pie(
        filtered_df,
        values='Debit',
        names='Custom Category',
        color='Custom Category',
        color_discrete_map=CATEGORY_COLORS,
        title=f"Spending Breakdown for {selected_month}",
    )
    pie_chart.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1c1f26",
        plot_bgcolor="#1c1f26",
        font_color="#e6e8eb",
        legend_font_color="#e6e8eb",
    )

    # Compute Total Spending and Payments
    total_spent = filtered_df["Debit"].sum()
    total_paid = filtered_df["Credit"].sum()

    return html.Div([
        dash_table.DataTable(
            data=filtered_df.to_dict('records'),
            page_size=10,
            sort_action="native",
            style_header={
                'backgroundColor': '#1c1f26',
                'color': '#9aa4b2',
                'fontWeight': 'bold',
                'border': '1px solid #2e333d',
            },
            style_cell={
                'backgroundColor': '#1c1f26',
                'color': '#e6e8eb',
                'border': '1px solid #2e333d',
                'textAlign': 'left',
                'padding': '8px',
            },
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': '#191c22'},
            ],
        ),
        dcc.Graph(figure=pie_chart),
        html.H3(f"Total Spending: ${total_spent:,.2f}"),
        html.H3(f"Total Paid: ${total_paid:,.2f}")
    ])

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
