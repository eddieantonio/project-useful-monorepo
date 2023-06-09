#!/usr/bin/env python3

"""
pickle-sample.py -- pickles the source code of a sample of scenarios

SYNOPSIS
    pickle-sample.py

REQUIREMENTS:
    sample.tsv
    **MUST BE RUN ON white.bluej.org!**

DESCRIPTION:
    This will read sample.tsv for a series of scenarios, and create a Python pickle file
    that contains the full source code of that scenario and its javac error messages.

SEE ALSO:
    sample-pem-index.py -- creates sample.tsv
"""

import pickle

from blackbox_mini import JavaUnit

sample_with_source_code = []
with open("sample.tsv") as sample_tsv:
    for line in sample_tsv:
        pem_category, xml_filename, version = line.rstrip().split("\t")
        unit = JavaUnit.from_path_and_version(xml_filename, version)
        sample_with_source_code.append(
            dict(
                pem_category=pem_category,
                # NOTE: [2023-05-11] This should be called "srcml_path", but it's too
                # late to change it now. So whenever you see "xml_filename", just think
                # "srcml_path" instead.
                xml_filename=xml_filename,
                version=version,
                unit=unit,
            )
        )

with open("sample.pickle", "wb") as sample_pickle:
    pickle.dump(sample_with_source_code, sample_pickle)
