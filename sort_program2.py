import pandas as pd
import os

# Define the path to the custom categories folder
CATEGORY_FOLDER = "custom_categories"

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
    df_parsed = pd.DataFrame()
    df_parsed['Transaction Date'] = pd.to_datetime(df['Transaction Date'])
    df_parsed['Description'] = df['Description']
    df_parsed['Category'] = df['Category']
    df_parsed['Amount'] = df['Debit'].fillna(0) - df['Credit'].fillna(0)
    df_parsed['Bank'] = 'Capital One'
    return df_parsed


def parse_us_bank(df):
    """Parse US Bank CSV format"""
    df_parsed = pd.DataFrame()
    df_parsed['Transaction Date'] = pd.to_datetime(df['Date'])
    df_parsed['Description'] = df['Name']
    df_parsed['Category'] = df['Transaction']
    df_parsed['Amount'] = df['Amount'].astype(float).abs()
    df_parsed['Bank'] = 'US Bank'
    return df_parsed


def parse_barclays(filepath):
    """Parse Barclays CSV format - has header rows that need to be skipped"""
    with open(filepath, 'r') as f:
        lines = f.readlines()
        skip_rows = 0
        for i, line in enumerate(lines):
            if 'Transaction Date' in line:
                skip_rows = i
                break
    
    df = pd.read_csv(filepath, skiprows=skip_rows)
    df_parsed = pd.DataFrame()
    df_parsed['Transaction Date'] = pd.to_datetime(df['Transaction Date'], format='%m/%d/%Y')
    df_parsed['Description'] = df['Description']
    df_parsed['Category'] = df['Category']
    df_parsed['Amount'] = df['Amount'].astype(float).abs()
    df_parsed['Bank'] = 'Barclays'
    return df_parsed


def parse_discover(df):
    """Parse Discover CSV format"""
    df_parsed = pd.DataFrame()
    df_parsed['Transaction Date'] = pd.to_datetime(df['Trans. Date'])
    df_parsed['Description'] = df['Description']
    df_parsed['Category'] = df['Category']
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
            bank_format = detect_bank_format(filepath)
            print(f"  Detected format: {bank_format}")
            
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
    
    if all_dfs:
        df_combined = pd.concat(all_dfs, ignore_index=True)
        print(f"\nTotal transactions loaded: {len(df_combined)}")
        return df_combined
    else:
        print("No valid data files found!")
        return pd.DataFrame()


def remove_internal_payments(df):
    """Remove payments between your own accounts"""
    payment_keywords = [
        'payment received',
        'payment thank you',
        'directpay',
        'autopay',
        'web authorized pmt',
        'online payment',
        'credit card payment',
        'discover',
        'capital one',
        'barclaycard',
        'barclay',
        'payment - thank you'
    ]
    
    keep_mask = df['Description'].str.lower().apply(
        lambda x: not any(keyword in x for keyword in payment_keywords)
    )
    
    removed_count = (~keep_mask).sum()
    print(f"\nRemoved {removed_count} internal payment transactions")
    
    return df[keep_mask].copy()


def load_categories():
    """Load category mappings from text files"""
    categories = {}
    category_names = []
    
    if not os.path.exists(CATEGORY_FOLDER):
        os.makedirs(CATEGORY_FOLDER)
        print(f"Created {CATEGORY_FOLDER} directory")
    
    print("\nCategories:", os.listdir(os.path.join(os.path.abspath("."), CATEGORY_FOLDER)))
    
    for file in os.listdir(os.path.join(os.path.abspath("."), CATEGORY_FOLDER)):
        if file.endswith(".txt"):
            category_name = file.replace(".txt", "")
            category_names.append(category_name)
            with open(os.path.join(CATEGORY_FOLDER, file), "r") as f:
                vendors = [line.strip() for line in f.readlines()]
            for vendor in vendors:
                categories[vendor.lower()] = category_name
    
    return categories, category_names


def save_vendor_to_category(vendor, category_name):
    """Save new vendor to the appropriate category file"""
    file_path = os.path.join(CATEGORY_FOLDER, f"{category_name}.txt")
    with open(file_path, "a") as f:
        f.write(vendor + "\n")


def get_category_selection(vendor, category_names):
    """Get user selection for categorization"""
    category_list = category_names + ["Other (Enter new category)", "Skip this vendor"]
    
    print("\nSelect a category for this vendor:")
    for i, cat in enumerate(category_list, 1):
        print(f"{i}. {cat}")
    
    while True:
        try:
            choice = int(input(f"Enter your choice (1-{len(category_list)}): "))
            if 1 <= choice <= len(category_list):
                break
            else:
                print(f"Please enter a number between 1 and {len(category_list)}")
        except ValueError:
            print("Please enter a valid number")
    
    if choice == len(category_list):  # Skip
        return None, category_names
    elif choice == len(category_list) - 1:  # User chooses "Other"
        new_category = input("Enter new category name: ")
        category_names.append(new_category)
        return new_category, category_names
    else:
        return category_list[choice - 1], category_names


# Main script
print("="*50)
print("VENDOR CATEGORIZATION SCRIPT")
print("="*50)

# Load all transactions
df = load_all_transactions()

if df.empty:
    print("No transactions to process!")
    exit()

# Remove internal payments
df = remove_internal_payments(df)

# Load existing categories
categories, category_names = load_categories()

# Add Custom Category column
df['Custom Category'] = 'Unknown'

# Track progress
total_vendors = len(df)
uncategorized_vendors = set()

# First pass: identify all uncategorized vendors
print("\n" + "="*50)
print("IDENTIFYING UNCATEGORIZED VENDORS")
print("="*50)

for index, row in df.iterrows():
    vendor = row['Description'].strip().lower()
    if vendor in categories:
        df.at[index, 'Custom Category'] = categories[vendor]
    else:
        uncategorized_vendors.add(vendor)

print(f"\nFound {len(uncategorized_vendors)} unique uncategorized vendors")
print(f"Total transactions to categorize: {df[df['Custom Category'] == 'Unknown'].shape[0]}")

# Second pass: categorize unknown vendors
if uncategorized_vendors:
    print("\n" + "="*50)
    print("CATEGORIZING VENDORS")
    print("="*50)
    
    for vendor in sorted(uncategorized_vendors):
        # Find a sample transaction for this vendor
        sample = df[df['Description'].str.lower() == vendor].iloc[0]
        
        print(f"\nVendor: {sample['Description']}")
        print(f"Sample Transaction: {sample['Transaction Date'].strftime('%Y-%m-%d')} | ${sample['Amount']:.2f} | {sample['Category']} | {sample['Bank']}")
        
        category, category_names = get_category_selection(sample['Description'], category_names)
        
        if category:  # Only save if not skipped
            # Update all transactions with this vendor
            mask = df['Description'].str.lower() == vendor
            df.loc[mask, 'Custom Category'] = category
            save_vendor_to_category(vendor, category)
            print(f"✓ Saved '{vendor}' to category '{category}'")
        else:
            print(f"⊘ Skipped '{vendor}'")

# Save the categorized transactions back to CSV
output_file = "data/categorized_transactions.csv"
df.to_csv(output_file, index=False)

print("\n" + "="*50)
print("CATEGORIZATION COMPLETE!")
print("="*50)
print(f"Saved to '{output_file}'")
print(f"Total transactions: {len(df)}")
print(f"Categorized: {len(df[df['Custom Category'] != 'Unknown'])}")
print(f"Uncategorized: {len(df[df['Custom Category'] == 'Unknown'])}")