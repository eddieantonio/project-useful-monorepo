#!/usr/bin/env python3

"""
combine-answers.py -- combines answers from different raters into one database.

REQUIREMENTS:
    *-answers.sqlite3 -- answers databases from each rater
    sample.pickle     -- the scenarios

DESCRIPTION:
    Combine the answers from different databases into one database. If
    answers.sqlite3 already exists, this will crash.
    The answers will be split from the ones taken from the pilot set and the one
    used for the "full set". The full set are the ones that should be used for analysis,
    but this data is a little bit messier than the neat pilot set.

OUTPUTS:
    answers.sqlite3 -- combined answers database
"""

import sqlite3
from pathlib import Path

from assign_scenarios import create_assignments


N_RATERS = 3
N_RESPONSES = 40

HERE = Path(__file__).parent

assert not (
    HERE / "answers.sqlite3"
).exists(), "not overwriting existing answers.sqlite3"

# Copy one database to use as our base
databases = list(HERE.glob("*-answers.sqlite3"))
assert len(databases) == N_RATERS, f"expected {N_RATERS} databases"

# Copy the schema from any of the databses to create the new database
example_database = databases[0]
conn = sqlite3.connect(example_database)
# We want two tables: answers and pilot_set_answers with the SAME schema
answers_schema = conn.execute(
    "SELECT sql FROM sqlite_schema WHERE name = 'answers'"
).fetchone()[0]
answers_schema += ";"
pilot_answers_schema = answers_schema.replace("[answers]", "[pilot_set_answers]", 1)
schema = answers_schema + "\n" + pilot_answers_schema
print(schema)
conn.close()

# Create the new database
conn = sqlite3.connect("answers.sqlite3")
conn.executescript(schema)

# Figure out which scenarios belong to the pilot set
pilot_set = set()
# Pilot set is the top 5 PEMs, 3 scenarios per category:
for rater in create_assignments(5, 3):
    for scenario in rater:
        pilot_set.add((scenario["xml_filename"], scenario["version"]))

# Create a table with the pilot set:
with conn:
    conn.executescript(
        """
        CREATE TABLE pilot_set (srcml_path TEXT, version TEXT);
        """
    )
    conn.executemany("INSERT INTO pilot_set VALUES (?, ?)", pilot_set)


# Okay, add all the answers to their respective tables
for database_path in databases:
    print(f"Attaching to {database_path}...")
    conn.execute(f"ATTACH DATABASE '{database_path}' AS other")

    with conn:
        # Full set:
        conn.execute(
            """
            INSERT INTO answers SELECT * FROM other.answers
            WHERE (srcml_path, version) NOT IN (SELECT * FROM pilot_set)
            """
        )
        # Pilot set:
        conn.execute(
            """
            INSERT INTO pilot_set_answers SELECT * FROM other.answers
            WHERE (srcml_path, version) IN (SELECT * FROM pilot_set)
            """
        )

    conn.execute("DETACH other")

COUNT_OF_ANSWERS = conn.execute("SELECT COUNT(*) FROM answers").fetchone()[0]
assert COUNT_OF_ANSWERS >= N_RATERS * N_RESPONSES
