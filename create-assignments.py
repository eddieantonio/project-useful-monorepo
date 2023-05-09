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

import pickle
from collections import defaultdict

# How many of the top PEMs should we collect
TOP_N = 10
# How many of each category we should collect
K = 9

# Top PEM categories, in order from most frequent to least frequent
TOP_ERRORS = [
    ("compiler.err.premature.eof"),
    ("';' expected"),
    ("compiler.err.cant.resolve[variable]"),
    ("compiler.err.illegal.start.of.expr"),
    ("<identifier> expected"),
    ("compiler.err.cant.resolve[method]"),
    ("compiler.err.cant.resolve[class]"),
    ("compiler.err.not.stmt"),
    ("class, interface, or enum expected"),
    ("')' expected"),
    ("compiler.err.prob.found.req"),
    ("compiler.err.missing.ret.stmt"),
    ("compiler.err.cant.apply.symbol"),
    ("compiler.err.invalid.meth.decl.ret.type.req"),
    ("compiler.err.doesnt.exist"),
    ("compiler.err.illegal.start.of.type"),
    ("compiler.err.unclosed.str.lit"),
    ("'(' expected"),
    ("compiler.err.already.defined[variable]"),
    ("compiler.err.illegal.start.of.stmt"),
]

with open("sample.pickle", "rb") as f:
    ALL_SCENARIOS = pickle.load(f)


def create_assignments(top_n: int, k: int):
    """
    Create assignments for the top N error message categories. k MUST be a multiple of
    3 such that we can divide the assignments in thirds.
    """

    # How many scenarios will be evaluated in total:
    total = top_n * k
    assert k % 3 == 0, "Number of scenarios per category must be divisible by 3 raters"

    # Group all scenarios by PEM category
    scenarios = defaultdict(list)
    for scenario in ALL_SCENARIOS:
        scenarios[scenario["pem_category"]].append(scenario)

    # Time to assign scenarios to raters!
    rater1 = []
    rater2 = []
    rater3 = []
    for category in TOP_ERRORS[:TOP_N]:
        # Retain only the top K scenarios from each category
        for i, scenario in enumerate(scenarios[category][:K]):
            # Rater 1 gets first 2/3
            # Rater 2 gets last 2/3
            # Rater 3 gets first 1/3 and last 1/3
            third = i % 3
            if third == 0:
                rater1.append(scenario)
                rater3.append(scenario)
            elif third == 1:
                rater1.append(scenario)
                rater2.append(scenario)
            else:
                rater2.append(scenario)
                rater3.append(scenario)

    one_third = total // 3
    assert len(rater1) == len(rater2) == len(rater3) == one_third * 2

    return rater1, rater2, rater3


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
