#!/usr/bin/env python3

"""
combine-answers.py -- combines answers from different raters into one database.

REQUIREMENTS:
    *-answers.sqlite3 -- answers databases from each rater

DESCRIPTION:
    Combine the answers from different databases into one database. If
    answers.sqlite3 already exists, this will crash.

OUTPUTS:
    answers.sqlite3 -- combined answers database
"""

import shutil
import sqlite3
from pathlib import Path

N_RATERS = 3
N_RESPONSES = 40

HERE = Path(__file__).parent

assert not (
    HERE / "answers.sqlite3"
).exists(), "not overwriting existing answers.sqlite3"

# Copy one database to use as our base
databases = list(HERE.glob("*-answers.sqlite3"))
assert len(databases) == N_RATERS, f"expected {N_RATERS} databases"
base_database = databases.pop(0)
print(f"Using {base_database} as base...")
shutil.copy(base_database, "answers.sqlite3")

conn = sqlite3.connect("answers.sqlite3")
for database_path in databases:
    print(f"Attaching to {database_path}...")
    conn.execute(f"ATTACH DATABASE '{database_path}' AS other")
    with conn:
        conn.execute("INSERT INTO answers SELECT * FROM other.answers")
    conn.execute("DETACH other")

COUNT_OF_ANSWERS = conn.execute("SELECT COUNT(*) FROM answers").fetchone()[0]
assert COUNT_OF_ANSWERS == N_RATERS * N_RESPONSES
