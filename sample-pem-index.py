#!/usr/bin/env python3

"""
sample-pem-index.py -- prints a sample of K messages from the PEM index

SYNOPSIS
    sample-pem-index.py [k]

REQUIREMENTS:
    pem-index.pickle

DESCRIPTION:

    This will print a sample of K PEM+context for each PEM category in the index. The
    output can be either
        a) saved as a .tsv; or
        b) copied pasted to be used with bbm-view on white.bluej.org.

    Examples:

        $ ./sample-pem-index.py 1
        compiler.err.premature.eof /data/mini/srcml-2021-03/project-22765860/src-114459139.xml 546279322
        compiler.err.not.stmt /data/mini/srcml-2013-12/project-815576/src-3411898.xml 119840851
        compiler.err.illegal.start.of.stmt /data/mini/srcml-2018-06/project-12842950/src-61847488.xml 2490587395

SEE ALSO:
    create-pem-index.py
"""

import pickle
import random
import sys

try:
    K = int(sys.argv[1])
except IndexError:
    # This is actually way more than I want, but whatever
    K = 20


with open("pem-index.pickle", "rb") as f:
    pem_index = pickle.load(f)

for pem, code_contexts in pem_index.items():
    sequence = list(code_contexts)
    sample = random.sample(sequence, K)

    for srcml_path, version in sample:
        print(f"{pem}\t{srcml_path}\t{version}")
