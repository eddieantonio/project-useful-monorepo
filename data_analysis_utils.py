"""
Additional utilities for the data analysis. These can be debugged separately.
"""


def agreement_as_label(kappa):
    """
    Gives you one or more labels for the agreement level between two raters.

    There are lots of conventions, so we'll just ouput ALL of the labels thay apply.

    See https://commons.wikimedia.org/wiki/File:Comparison_of_rubrics_for_evaluating_inter-rater_kappa_(and_intra-class_correlation)_coefficients.png
    """

    labels = set()

    assert 0 <= kappa <= 1

    # Cichetti & Sparrow, 1981
    if 0 <= kappa < 0.4:
        labels.add("Poor")
    elif 0.4 <= kappa < 0.6:
        labels.add("Fair")
    elif 0.6 <= kappa < 0.75:
        labels.add("Good")
    elif 0.75 <= kappa <= 1:
        labels.add("Excellent")

    # Fleiss, 1981
    if 0 <= kappa < 0.4:
        labels.add("Poor")
    elif 0.4 <= kappa < 0.75:
        labels.add("Intermediate")
    elif 0.75 <= kappa <= 1:
        labels.add("Excellent")

    # Landis & Koch, 1977
    if 0 <= kappa < 0.2:
        labels.add("Slight")
    elif 0.2 <= kappa < 0.4:
        labels.add("Fair")
    elif 0.4 <= kappa < 0.6:
        labels.add("Moderate")
    elif 0.6 <= kappa < 0.8:
        labels.add("Substantial")
    elif 0.8 <= kappa <= 1:
        labels.add("Almost Perfect")

    # Regier et al., 2012
    if 0 <= kappa < 0.2:
        labels.add("Unacceptable")
    elif 0.2 <= kappa < 0.4:
        labels.add("Questionable")
    elif 0.4 <= kappa < 0.6:
        labels.add("Good")
    elif 0.6 <= kappa < 0.8:
        labels.add("Very Good")
    elif 0.8 <= kappa <= 1:
        labels.add("Excellent")

    return labels
