import os
import csv

filename = input("Enter the name of the file to load in, or X if you wish to run only on previous data: ")

if filename != "X":
    with open(os.path.join(os.path.abspath("."), "data", filename), "r") as file:
        reader = csv.reader(file)
        for row in reader:
            