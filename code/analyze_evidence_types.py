import os
import csv
import json
import sqlite3
import re

with open('dataset/evidence_files.csv', mode='r', encoding='utf-8') as f:
    files = list(csv.DictReader(f))

types = {}
for f in files:
    ext = os.path.splitext(f['file_path'])[1].lower()
    types[ext] = types.get(ext, 0) + 1

print("Evidence types:", types)
