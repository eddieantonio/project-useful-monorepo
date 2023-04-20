#!/usr/bin/env python3

"""
create-pem-index.py -- builds an index from PEM category to an instance of that PEM.

REQUIREMENTS:
    useful.sqlite3

OUTPUTS:
    pem-index.pickle

DESCRIPTION:

    This will create an index that maps a PEM category (for example, ';' expected) to
    ALL of the "elligible" error messages in Blackbox Mini. What ellible means depends
    entirely on the data in usefule.sqlite3.

    This will look something like this:

        pem_index = {
            "';' expected": {
                ("/data/mini/srcml-2019-12/project-18399210/src-89869230.xml", 3967647149),
                ("/data/mini/srcml-2020-12/project-21874619/src-109148661.xml", 5129211943),
                ...
            }
            ...
        }

SEE ALSO:
    create-useful-database.py
    sample-pem-index.py
"""

import pickle
import sqlite3
from collections import defaultdict

conn = sqlite3.connect("useful.sqlite3")

pem_to_paths = defaultdict(set)

cur = conn.execute(
    """
    SELECT COALESCE(javac_name, sanitized_text) as identifier,
           srcml_path,
           version
      FROM messages
"""
)

for identifier, srcml_path, version in cur:
    pem_to_paths[identifier].add((srcml_path, version))

with open("pem-index.pickle", "wb") as f:
    pickle.dump(pem_to_paths, f)
