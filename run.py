import os
import csv
import sqlite3

# basic setup
filename = input("Enter the name of the file to load in, or X if you wish to run only on previous data: ")
con = sqlite3.connect("transactions.db")
cur = con.cursor()
try:
    cur.execute("CREATE TABLE transactions(transaction_date, post_date, card, name, category, debit, credit)")
except sqlite3.OperationalError as e:
    print("Database already exists")

# read new data in if indicated
if filename != "X":
    with open(os.path.join(os.path.abspath("."), "data", filename), "r") as file:
        reader = csv.reader(file)
        FIRST = True
        for row in reader:
            #print(row)
            if FIRST:
                FIRST = False
                continue
            else:
                clean_row = [x.replace("'","").strip() for x in row]
                data = "'" + "', '".join(clean_row) + "'"
                #print(data)
                cur.execute("INSERT INTO transactions VALUES (" + data + ")")
                con.commit()

# now that the data is contained, visualize it
else:
    print("visualizing")