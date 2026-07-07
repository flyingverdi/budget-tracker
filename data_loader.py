import os
import pandas as pd

# Standard schema used throughout the app (Capital One export format)
STANDARD_COLUMNS = ['Transaction Date', 'Posted Date', 'Card No.', 'Description', 'Category', 'Debit', 'Credit']

# Folder of category files. Each file is "<Category>.txt" containing one lowercase
# keyword per line; a transaction is assigned the category whose keyword appears as
# a substring of its description (longest matching keyword wins).
CATEGORY_FOLDER = "custom_categories"

# Descriptions dropped from the collected spending view entirely: credit-card
# payments/paydowns, deposits/income, and personal transfers. These are money
# moving between the user's own accounts (or income), not spending, and would
# otherwise double-count against the individual purchases.
#
# Matched as case-insensitive substrings, but ONLY for transactions that did not
# already match a real spending category. That ordering is deliberate: e.g. the
# rent payment "ZELLE INSTANT PMT TO RIMA" matches the Rent category first and is
# kept, while any other "ZELLE INSTANT PMT" is treated as a transfer and dropped.
EXCLUDE_PATTERNS = [
    # credit-card payments / paydowns
    'directpay', 'internet payment', 'autopay pymt', 'online pymt', 'mobile pymt',
    'web authorized pmt discover', 'web authorized pmt capital one', 'web authorized pmt barclaycard',
    'capital one mobile pymt',
    # deposits / income
    'electronic deposit', 'interest paid', 'mobile deposit', 'payroll',
    # personal transfers
    'returned mobile ach', 'zelle instant pmt',
]

# Fallback used when no keyword matches: map the card issuer's own category to one
# of ours. Deliberately conservative — vague issuer buckets (Merchandise, Other
# Services, ...) are left out so they surface as "Unknown" rather than be guessed.
BANKCAT_FALLBACK = {
    'Dining': 'Dining', 'Restaurants': 'Dining', 'Supermarkets': 'Grocery',
    'Gas/Automotive': 'Gas', 'Gasoline': 'Gas', 'Automotive': 'Tools and Automotive',
    'Other Travel': 'Travel', 'Lodging': 'Travel', 'Airfare': 'Travel', 'Car Rental': 'Travel',
    'Travel/ Entertainment': 'Travel', 'Entertainment': 'Entertainment',
    'Home Improvement': 'Home Improvement', 'Health Care': 'Self Care', 'Medical Services': 'Self Care',
    'Insurance': 'Bills and Taxes', 'Phone/Cable': 'Bills and Taxes', 'Utilities': 'Bills and Taxes',
    'Internet': 'Bills and Taxes',
}


def is_excluded(description):
    """True if a description is a card payment, deposit/income, or transfer."""
    text = str(description).lower()
    return any(pattern in text for pattern in EXCLUDE_PATTERNS)


def load_category_keywords(folder=CATEGORY_FOLDER):
    """Read the category files into a list of (keyword, category) pairs.

    Returns the pairs plus the sorted list of category names. Pairs are sorted by
    descending keyword length so the first substring match is also the most
    specific one (e.g. "king soopers fue" -> Gas beats "king soopers" -> Grocery).
    """
    pairs = []
    category_names = []
    for file in sorted(os.listdir(folder)):
        if not file.endswith(".txt"):
            continue
        category = file[:-len(".txt")]
        category_names.append(category)
        with open(os.path.join(folder, file)) as f:
            for line in f:
                keyword = line.strip().lower()
                if keyword:
                    pairs.append((keyword, category))
    pairs.sort(key=lambda kc: len(kc[0]), reverse=True)
    return pairs, category_names


def categorize_description(description, pairs):
    """Return the category for a description, or None if no keyword matches."""
    text = str(description).lower()
    for keyword, category in pairs:  # pairs are longest-keyword-first
        if keyword in text:
            return category
    return None


def _normalize_discover(df):
    """Convert a Discover export into the standard schema.

    Discover columns: Trans. Date, Post Date, Description, Amount, Category
      - dates are MM/DD/YYYY
      - Amount is a single signed value: positive = charge (Debit),
        negative = payment/credit (Credit)
      - there is no card number
    """
    df = df.rename(columns={'Trans. Date': 'Transaction Date', 'Post Date': 'Posted Date'})

    amount = pd.to_numeric(df['Amount'], errors='coerce')
    df['Debit'] = amount.where(amount > 0)
    df['Credit'] = (-amount).where(amount < 0)
    df['Card No.'] = pd.NA  # Discover does not provide a card number

    return df[STANDARD_COLUMNS]


def _normalize_usbank(df):
    """Convert a US Bank checking export into the standard schema.

    US Bank columns: Date, Transaction, Name, Memo, Amount
      - a single date is used for both transaction and posted date
      - Amount is a single signed value: negative = money out (Debit/spending),
        positive = money in (Credit/deposit)
      - Name is the merchant/description; there is no card number or bank category
    """
    df = df.rename(columns={'Date': 'Transaction Date', 'Name': 'Description'})
    df['Posted Date'] = df['Transaction Date']

    amount = pd.to_numeric(df['Amount'], errors='coerce')
    df['Debit'] = (-amount).where(amount < 0)
    df['Credit'] = amount.where(amount > 0)
    df['Card No.'] = pd.NA          # checking account, no card number
    df['Category'] = 'Checking'     # US Bank export has no category column

    return df[STANDARD_COLUMNS]


def read_transactions(path):
    """Read a single transactions CSV and return it in the standard schema.

    Detects the Discover and US Bank formats by their column names and converts
    them; any other file is assumed to already use the standard schema.
    """
    df = pd.read_csv(path)
    columns = set(df.columns)

    if {'Trans. Date', 'Post Date', 'Amount'}.issubset(columns):
        df = _normalize_discover(df)
    elif {'Date', 'Name', 'Memo', 'Amount'}.issubset(columns):
        df = _normalize_usbank(df)

    # Normalize dates to ISO strings so files with different date formats
    # concatenate and parse consistently.
    for col in ('Transaction Date', 'Posted Date'):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d')

    return df


def load_all_transactions(data_path):
    """Read and concatenate every CSV in data_path into one standard-schema frame."""
    files = [f for f in os.listdir(data_path) if f.endswith('.csv')]
    df_list = [read_transactions(os.path.join(data_path, file)) for file in files]
    return pd.concat(df_list, ignore_index=True)


def categorize_transactions(df, pairs=None):
    """Assign a 'Custom Category' to every row and drop excluded rows.

    Categorization order for each row:
      1. keyword match against the category files (most specific keyword wins)
      2. otherwise, if the description is a payment/income/transfer, drop it
      3. otherwise, fall back to the card issuer's own category if we map it
      4. otherwise, 'Unknown'
    """
    if pairs is None:
        pairs, _ = load_category_keywords()

    def classify(row):
        category = categorize_description(row['Description'], pairs)
        if category is not None:
            return category
        if is_excluded(row['Description']):
            return None  # marked for removal
        bank_category = row.get('Category')
        if pd.notna(bank_category) and bank_category in BANKCAT_FALLBACK:
            return BANKCAT_FALLBACK[bank_category]
        return 'Unknown'

    df = df.copy()
    df['Custom Category'] = df.apply(classify, axis=1)
    df = df[df['Custom Category'].notna()].reset_index(drop=True)
    return df
