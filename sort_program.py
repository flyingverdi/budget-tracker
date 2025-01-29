import pandas as pd
import os

# Load all CSV files in 'data' folder
data_path = os.path.join(os.path.abspath("."), "data")
files = [f for f in os.listdir(data_path) if f.endswith('.csv')]

# Read and concatenate all CSV files into one DataFrame
df_list = [pd.read_csv(os.path.join(data_path, file)) for file in files]
df = pd.concat(df_list, ignore_index=True)

# Define the path to the custom categories folder
CATEGORY_FOLDER = "custom_categories"

# Load category mappings from text files
def load_categories():
    categories = {}
    category_names = []
    print(" Categories:", os.listdir(os.path.join(os.path.abspath("."),CATEGORY_FOLDER)))
    for file in os.listdir(os.path.join(os.path.abspath("."),CATEGORY_FOLDER)):
        if file.endswith(".txt"):
            category_name = file.replace(".txt", "")
            category_names.append(category_name)
            with open(os.path.join(CATEGORY_FOLDER, file), "r") as f:
                vendors = [line.strip() for line in f.readlines()]
                for vendor in vendors:
                    categories[vendor.lower()] = category_name
    return categories, category_names

# Save new vendor to the appropriate category file
def save_vendor_to_category(vendor, category_name):
    file_path = os.path.join(CATEGORY_FOLDER, f"{category_name}.txt")
    with open(file_path, "a") as f:
        f.write(vendor + "\n")

# Get user selection for categorization
def get_category_selection(vendor, category_names):
    category_list = category_names + ["Other (Enter new category)"]
    
    print("\nSelect a category for this vendor:")
    for i, cat in enumerate(category_list, 1):
        print(f"{i}. {cat}")
    
    choice = int(input("Enter your choice (1-{}): ".format(len(category_list))))
    
    if choice == len(category_list):  # User chooses "Other"
        new_category = input("Enter new category name: ")
        category_names.append(new_category)
        return new_category, category_names
    else:
        return category_list[choice - 1], category_names

# Load existing categories
categories, category_names = load_categories()

for index, row in df.iterrows():
    vendor = row['Description'].strip().lower()
    if vendor in categories:
        df.at[index, 'Custom Category'] = categories[vendor]
    else:
        print(f"\nTransaction: {row['Transaction Date']} | {vendor} | ${row['Debit']} | ${row['Credit']} |  {row['Category']}")
        category, category_names = get_category_selection(row['Description'], category_names)
        df.at[index, 'Custom Category'] = category
        save_vendor_to_category(vendor, category)

# Save the categorized transactions back to CSV
df.to_csv("data/categorized_transactions.csv", index=False)
print("\nCategorization complete! Saved to 'categorized_transactions.csv'.")
