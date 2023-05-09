#!/usr/bin/env python3

"""
create-assignments.py -- assigns scenarios to raters.

REQUIREMENTS:
    sample.pickle

DESCRIPTION:
    This will partition the scenarios such that each scenario is assigned to at
    least 2 raters. Each rater will see at least one scenario from each PEM category.
    That is, scenarios from each category will be distributed evenly across raters.

OUTPUTS:
    {rater}-assignments.tsv
"""


from assign_scenarios import create_assignments

# How many of the top PEMs should we collect
TOP_N = 10
# How many of each category we should collect
K = 9


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


if __name__ == "__main__":
    rater1, rater2, rater3 = create_assignments(TOP_N, K)
    save_assignments(rater1, rater2, rater3)
