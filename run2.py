# Import packages
from dash import Dash, html, dash_table, dcc, callback, Input, Output
import pandas as pd
import plotly.express as px
import os

# Define the path to the custom categories folder
CATEGORY_FOLDER = "custom_categories"

# Load category mappings from text files
def load_categories():
    categories = {}
    category_names = []
    print("Categories:", os.listdir(os.path.join(os.path.abspath("."), CATEGORY_FOLDER)))
    for file in os.listdir(os.path.join(os.path.abspath("."), CATEGORY_FOLDER)):
        if file.endswith(".txt"):
            category_name = file.replace(".txt", "")
            category_names.append(category_name)
            with open(os.path.join(CATEGORY_FOLDER, file), "r") as f:
                vendors = [line.strip() for line in f.readlines()]
            for vendor in vendors:
                categories[vendor.lower()] = category_name
    return categories, category_names


def detect_bank_format(filepath):
    """
    Detect which bank format the CSV is based on file content.
    Returns: 'capital_one', 'us_bank', 'barclays', 'discover', or 'unknown'
    """
    # Read first few lines to check for Barclays header
    with open(filepath, 'r') as f:
        first_lines = [f.readline() for _ in range(5)]
    
    # Barclays: Has "Barclays Bank Delaware" in first line
    if any('Barclays' in line for line in first_lines[:3]):
        return 'barclays'
    
    # Now try reading as CSV to check columns
    try:
        df_sample = pd.read_csv(filepath, nrows=2)
        columns = [col.strip().lower() for col in df_sample.columns]
        
        # Capital One: Has 'Card No.' and 'Posted Date'
        if 'card no.' in columns and 'posted date' in columns:
            return 'capital_one'
        
        # US Bank: Has 'Transaction' and 'Memo' columns
        if 'transaction' in columns and 'memo' in columns:
            return 'us_bank'
        
        # Discover: Has 'Trans. Date' and 'Post Date'
        if 'trans. date' in columns and 'post date' in columns:
            return 'discover'
    
    except Exception as e:
        print(f"  Error detecting format: {e}")
    
    return 'unknown'


def parse_capital_one(df):
    """Parse Capital One CSV format"""
    # Rename columns to standard format
    df_parsed = pd.DataFrame()
    df_parsed['Transaction Date'] = pd.to_datetime(df['Transaction Date'])
    df_parsed['Description'] = df['Description']
    df_parsed['Category'] = df['Category']
    
    # Capital One uses separate Debit/Credit columns
    # Debit is positive (money spent), Credit is negative (refunds)
    df_parsed['Amount'] = df['Debit'].fillna(0) - df['Credit'].fillna(0)
    df_parsed['Bank'] = 'Capital One'
    
    return df_parsed


def parse_us_bank(df):
    """Parse US Bank CSV format"""
    df_parsed = pd.DataFrame()
    df_parsed['Transaction Date'] = pd.to_datetime(df['Date'])
    df_parsed['Description'] = df['Name']
    df_parsed['Category'] = df['Transaction']  # DEBIT/CREDIT type
    
    # Amount is already signed (negative = money out)
    df_parsed['Amount'] = -df['Amount'].astype(float)  # Make positive for spending
    df_parsed['Bank'] = 'US Bank'
    
    return df_parsed


def parse_barclays(filepath):
    """Parse Barclays CSV format - has header rows that need to be skipped"""
    # Find where the actual data starts
    with open(filepath, 'r') as f:
        lines = f.readlines()
        skip_rows = 0
        for i, line in enumerate(lines):
            if 'Transaction Date' in line:
                skip_rows = i
                break
    
    # Read the CSV starting from the data header
    df = pd.read_csv(filepath, skiprows=skip_rows)
    
    df_parsed = pd.DataFrame()
    df_parsed['Transaction Date'] = pd.to_datetime(df['Transaction Date'], format='%m/%d/%Y')
    df_parsed['Description'] = df['Description']
    df_parsed['Category'] = df['Category']
    
    # Amount: Positive for charges, negative for credits
    # Keep as positive for consistency
    df_parsed['Amount'] = df['Amount'].astype(float).abs()
    df_parsed['Bank'] = 'Barclays'
    
    return df_parsed


def parse_discover(df):
    """Parse Discover CSV format"""
    df_parsed = pd.DataFrame()
    df_parsed['Transaction Date'] = pd.to_datetime(df['Trans. Date'])
    df_parsed['Description'] = df['Description']
    df_parsed['Category'] = df['Category']
    
    # Amount: Negative for payments, positive for charges
    # Take absolute value to make all spending positive
    df_parsed['Amount'] = df['Amount'].astype(float).abs()
    df_parsed['Bank'] = 'Discover'
    
    return df_parsed


def load_all_transactions():
    """Load and parse all CSV files from data folder"""
    data_path = os.path.join(os.path.abspath("."), "data")
    files = [f for f in os.listdir(data_path) if f.endswith('.csv')]
    
    all_dfs = []
    
    for file in files:
        filepath = os.path.join(data_path, file)
        print(f"\nProcessing: {file}")
        
        try:
            # Detect format by examining file content
            bank_format = detect_bank_format(filepath)
            print(f"  Detected format: {bank_format}")
            
            # Parse based on detected format
            if bank_format == 'capital_one':
                df = pd.read_csv(filepath)
                df_parsed = parse_capital_one(df)
            
            elif bank_format == 'us_bank':
                df = pd.read_csv(filepath)
                df_parsed = parse_us_bank(df)
            
            elif bank_format == 'barclays':
                df_parsed = parse_barclays(filepath)
            
            elif bank_format == 'discover':
                df = pd.read_csv(filepath)
                df_parsed = parse_discover(df)
            
            else:
                print(f"  WARNING: Unknown format, skipping file")
                continue
            
            all_dfs.append(df_parsed)
            print(f"  Loaded {len(df_parsed)} transactions")
        
        except Exception as e:
            print(f"  ERROR processing {file}: {str(e)}")
            continue
    
    # Combine all dataframes
    if all_dfs:
        df_combined = pd.concat(all_dfs, ignore_index=True)
        print(f"\nTotal transactions loaded: {len(df_combined)}")
        return df_combined
    else:
        print("No valid data files found!")
        return pd.DataFrame()


# Load all transactions
df = load_all_transactions()

# Filter out internal payments between accounts
def remove_internal_payments(df):
    """
    Remove payments between your own accounts (e.g., bank to credit card payments)
    """
    # Common payment keywords to filter out
    payment_keywords = [
        'payment received',
        'payment thank you',
        'directpay',
        'autopay',
        'web authorized pmt',
        'online payment',
        'credit card payment',
        'discover',  # Payments to Discover card
        'capital one',  # Payments to Capital One
        'barclaycard',  # Payments to Barclays
        'barclay',
        'payment - thank you'
    ]
    
    # Create a mask for rows to keep (True = keep, False = remove)
    keep_mask = df['Description'].str.lower().apply(
        lambda x: not any(keyword in x for keyword in payment_keywords)
    )
    
    removed_count = (~keep_mask).sum()
    print(f"\nRemoved {removed_count} internal payment transactions")
    
    return df[keep_mask].copy()

# Remove internal payments
df = remove_internal_payments(df)

# Load categories and apply them
categories, _ = load_categories()

# Add Custom Category column
df['Custom Category'] = 'Unknown'

for index, row in df.iterrows():
    vendor = row['Description'].strip().lower()
    if vendor in categories:
        df.at[index, 'Custom Category'] = categories[vendor]

# Ensure proper data types and extract date components
df['Transaction Date'] = pd.to_datetime(df['Transaction Date'])
df['Year'] = df['Transaction Date'].dt.year.astype(str)
df['Month'] = df['Transaction Date'].dt.strftime('%B')

# Get sorted lists for dropdowns
years = sorted(df['Year'].unique(), reverse=True)
months = ['January', 'February', 'March', 'April', 'May', 'June', 
          'July', 'August', 'September', 'October', 'November', 'December']

# Remove duplicate transactions
df.drop_duplicates(subset=['Transaction Date', 'Description', 'Amount', 'Bank'], inplace=True)

print("\nData processing complete!")
print(f"Banks included: {df['Bank'].unique().tolist()}")
print(f"Date range: {df['Transaction Date'].min()} to {df['Transaction Date'].max()}")

# Initialize the app
app = Dash(__name__, suppress_callback_exceptions=True)

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

    # Filter data for selected year and month
    filtered_df = df[(df['Year'] == selected_year) & (df['Month'] == selected_month)]

    if filtered_df.empty:
        return html.Div("No transactions for this month.")

    # Generate Pie Chart using Amount and Custom Category
    pie_chart = px.pie(filtered_df, values='Amount', names='Custom Category', 
                       title=f"Spending Breakdown for {selected_month} {selected_year}")

    # Compute Total Spending
    total_spent = filtered_df["Amount"].sum()

    return html.Div([
        dash_table.DataTable(
            data=filtered_df.to_dict('records'), 
            page_size=10,
            sort_action="native",
            style_cell={'textAlign': 'left'},
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': 'rgb(248, 248, 248)'
                }
            ]
        ),
        dcc.Graph(figure=pie_chart),
        html.H3(f"Total Spending: ${total_spent:,.2f}")
    ])

# Run the app
if __name__ == '__main__':
    app.run(debug=True)