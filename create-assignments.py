#!/usr/bin/env python3

"""
create-assignments.py -- assigns scenarios to raters.

USAGE:
    create-assignments.py pilot-set     # top 5 PEMs, 3 scenarios per category
    create-assignments.py full-set      # top 10 PEMs, 9 scenarios per category

REQUIREMENTS:
    sample.pickle

DESCRIPTION:
    This will partition the scenarios such that each scenario is assigned to at
    least 2 raters. Each rater will see at least one scenario from each PEM category.
    That is, scenarios from each category will be distributed evenly across raters.

    Note: the full set is always a STRICT SUPERSET of the pilot set.

OUTPUTS:
    {rater}-assignments.tsv

SEE ALS:
    rate-pems.py -- uses the assignments to prompt raters
    assign_scenarios.py -- library that creates assignments
"""

import argparse

from assign_scenarios import create_assignments


def save_assignments(rater1, rater2, rater3):
    for assignments, name in zip(
        [rater1, rater2, rater3], ["eddie", "prajish", "brett"]
    ):
        with open(f"{name}-assignments.tsv", "w") as f:
            for scenario in assignments:
                pem_category = scenario["pem_category"]
                srcml_path = scenario["xml_filename"]
                version = scenario["version"]
                f.write(f"{pem_category}\t{srcml_path}\t{version}\n")


parser = argparse.ArgumentParser()
parser.add_argument("set", choices=["pilot-set", "full-set"])
args = parser.parse_args()

# How many of the top PEMs should we collect?
# How many scenarios of each category we should collect?
if args.set == "pilot-set":
    TOP_N = 5
    K = 3
else:
    # Full set
    TOP_N = 10
    K = 9

rater1, rater2, rater3 = create_assignments(TOP_N, K)
save_assignments(rater1, rater2, rater3)
