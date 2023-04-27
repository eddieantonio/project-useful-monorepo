#!/usr/bin/env python3

"""
rate-pems.py -- rate programming error messages

REQUIREMENTS:
    sample.pickle -- a sample of scenarios from Blackbox Mini
    llm.pickle -- enhanced error messages from GPT-4

DESCRIPTION:
    This will ask the user to rate programming error messages from javac,
    decaf, and two versions from GPT-4.
    This is an interactive, TUI application.

OUTPUT:
    answers.sqlite3 -- the recorded answers for each scenario and variant
    assignnments.tsv -- a list of "assigned" scenarios for each rater

SEE ALSO
    pickle-sample.py -- creates sample.pickle
    pickle-llm-results.py -- creates llm.pickle
"""

from itertools import groupby
import os
import pickle
import sys
import textwrap
from typing import Any, Dict, Literal, Sequence, TypedDict
from pathlib import Path

import questionary
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import JavaLexer
from questionary import Choice, ValidationError
from rich import print
from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text
from sqlite_utils import Database

from blackbox_mini import JavaUnit

# Rich console for pretty-printing:
console = Console()
console.width = min(120, console.width)

# Configure the JavaLexer so that it does not eat up empty lines!
java_lexer = JavaLexer(stripnl=False)
terminal_formatter = TerminalFormatter()


HERE = Path(__file__).parent.resolve()
ALL_VARIANTS = ("javac", "decaf", "gpt-4-error-only", "gpt-4-with-context")

### Types ###

# The four different error message variants:
Variant = Literal["javac", "decaf", "gpt-4-error-only", "gpt-4-with-context"]
Answers = Dict[str, int]


class Scenario(TypedDict):
    """
    A scenario is some erroneous Java code paired wth its programming error message.
    The Java code comes from a particular srcML file in the Blackbox Mini dataset,
    and can be uniquely identified using its XML path and version ID.

    This typed dict comes from the sample.pickle file.
    """

    pem_category: str
    # Also known as "scrml_path" in the useful.sqlite3 🤪
    xml_filename: str
    # I know this looks like an int, but it is, in fact, a string:
    version: str
    unit: JavaUnit


### Exceptions ###


class RaterQuitException(Exception):
    """
    Raised when the user quits the application.
    They could exit using Ctrl+C or Ctrl+D.
    """


class EnhancedMessageDoesNotExistException(Exception):
    """
    Raised when an enhanced error message does not exist for a particular
    variant.
    """


### Validators ###


class NonNegativeNumberValidator(questionary.Validator):
    """
    Require that a non-negative number has been entered.
    """

    def validate(self, document) -> None:
        try:
            number = int(document.text)
        except ValueError:
            raise ValidationError(message="Please enter a number")

        if number < 0:
            raise ValidationError(message="Please enter a non-negative number")

        return super().validate(document)


### Functions ###


def print_with_javac_pem(unit: JavaUnit) -> None:
    """
    Use pygments to pretty-print the Java source code to the terminal.
    """

    source_lines = highlight(
        unit.source_code, java_lexer, terminal_formatter
    ).splitlines()

    # Place a gutter on the side of the source code
    biggest_line_no_width = len(str(len(source_lines)))

    assert (
        len(unit.pems) >= 1
    ), f"There should be at least one PEM, but found {unit.pems!r}"
    pem = unit.pems[0]
    pem_line_no = pem.start.line

    for line_no, ansi_line in enumerate(source_lines, start=1):
        on_pem_line = line_no == pem_line_no
        line = Text.from_ansi(ansi_line)

        if not on_pem_line:
            # Ordinary line:
            print(f"{line_no:>{biggest_line_no_width}} | ", end="")
            print(line)
            continue

        # Priting the error message:
        print(f"[red]{pem.filename}: error: [bold]{pem.fixed_error_message_text}")
        # Print the line containing the error:
        print(f"[bold red]{line_no:>{biggest_line_no_width}}[/bold red] | ", end="")
        print(line)

        # Columns are 1-indexed (annoyingly):
        padding = (pem.start.column - 1) * " "
        margin = " " * biggest_line_no_width

        # Print the caret (looks like a red, squiggly underline):
        if pem.start.line == pem.end.line:
            marker = "^" * max(1, pem.end.column - pem.start.column)
        else:
            marker = "^"
        print(f"{margin} | {padding}[red]{marker}[/red]")
        print(f"{margin} |")


def print_source_code(scenario: Scenario):
    unit = scenario["unit"]

    # Fence off the source code:
    console.rule("[bold]Source code")
    print_with_javac_pem(unit)


def ask_about_scenario(scenario: Scenario, variants: Sequence[Variant]):
    """
    Asks the user to rate a scenario under various different variants.

    A scenario is some erroneous Java code, and a programming error message.
    A variant is one of the following:
     - javac (control)
     - gpt-4-error-only -- enhance only the error message text
     - gpt-4-with-context -- enhance the error message text with code context
     - decaf -- (not yet implemented!)
    """
    # This statement is not necessary, but is here to document that I'm abusing
    # global variables :)
    global answers_table, rater

    print_source_code(scenario)

    for variant in variants:
        print()
        # TODO: handle rater quit exception
        try:
            answers = ask_about_variant(scenario, variant)
        except EnhancedMessageDoesNotExistException:
            print(
                f"This error message does not exist for {variant}, so we're marking it as complete."
            )
            answers = {}

        answers_table.insert(
            {
                "srcml_path": scenario["xml_filename"],
                "version": scenario["version"],
                "variant": variant,
                "rater": rater,
                "answers": answers,
            }
        )


def ask_about_variant(scenario, variant: Variant) -> Answers:
    """
    Continue asking the user to rate a scenario under a particular variant until they are happy with their answers.
    """
    while True:
        answers = ask_about_variant_once(scenario, variant)

        print(answers)
        # I'm channelling Kaepora Gaebora energy here:
        answers_confirmed = questionary.confirm(
            "🦉 Are you sure you want to commit to these answers?",
            default=False,
            auto_enter=False,
        ).ask()

        if answers_confirmed is None:
            raise RaterQuitException

        if answers_confirmed:
            return answers
        else:
            print("Okay, we'll try that again!")


def ask_about_variant_once(scenario, variant: Variant) -> Answers:
    """
    Ask the user to rate a scenario under a particular variant.
    """
    unit = scenario["unit"]

    console.rule(
        f"[bold]Rate this {variant} error message for the above context[/bold]:"
    )

    # All the PEMs use the original javac error message:
    javac_error_message = unit.pems[0].fixed_error_message_text

    # Show the original javac message for reference:
    if variant in ("decaf", "gpt-4-error-only", "gpt-4-with-context"):
        print("[grey62 italic]Note: This is the original javac error message:")
        message_as_md_quote = textwrap.indent(javac_error_message, "> ")
        md = Markdown(message_as_md_quote)
        console.print(md)
        print()

    if variant == "javac":
        message = javac_error_message
        print(javac_error_message)
    elif variant == "gpt-4-error-only":
        message = GPT4_CODE_ONLY_RESPONSES[scenario["pem_category"]]
        md = Markdown(message)
        console.print(md)
    elif variant == "gpt-4-with-context":
        message = GPT4_CONTEXTUAL_RESPONSES.get(
            # I know, I know, it should be "srcml_path", but I accidentally
            # changed it to "xml_filename" in the pickle, so here we are:
            (scenario["xml_filename"], scenario["version"])
        )
        if message is None:
            raise RaterQuitException(
                "The source code context was too large to query GPT-4."
            )
        md = Markdown(message)
        console.print(md)
    elif variant == "decaf":
        raise NotImplementedError("Don't have Decaf PEMs yet")
    else:
        raise ValueError(f"Unknown configuration: {variant!r}")

    # Ask all the questions!
    console.rule()
    try:
        answers = ask_questions_for_current_variant()
    except (KeyboardInterrupt, EOFError):
        raise RaterQuitException

    answers.update(length=len(message))
    return answers


def ask_questions_for_current_variant() -> Answers:
    """
    Actually asks all the questions!

    Note: you must remember to add the message length to the answers after the fact!

    :throws KeyboardInterrupt: if the user inputs Ctrl-C
    """
    answers: Dict[str, Any] = {}

    # Denny et al. 2021 CHI paper readability factors
    answers.update(
        jargon=int(
            questionary.text(
                "How many jargon words are in this message?",
                validate=NonNegativeNumberValidator,
            ).unsafe_ask()
        ),
        sentence_structure=questionary.select(
            "Is this error message presented in well-structured sentences?",
            choices=[
                Choice(title="Clear, understanble sentences", value="clear"),
                Choice(title="Could be clearer", value="could-be-clearer"),
                Choice(title="Unclear, does not use full sentences", value="unclear"),
            ],
        ).unsafe_ask(),
    )
    # Note: length should be added by the caller

    # Leinonen et al. 2023 -- LLMs for PEMs
    answers.update(
        explanation=questionary.confirm(
            "Does this message provide an explanation for the error?",
        ).unsafe_ask()
    )

    if answers["explanation"]:
        answers.update(
            explanation_correctness=questionary.select(
                "Is the explanation correct?",
                choices=[
                    Choice(title="It is unmistakably correct", value="yes"),
                    Choice(title="Maybe/Depends on programmer's intent", value="maybe"),
                    Choice(title="It is definitely wrong", value="no"),
                ],
            ).unsafe_ask()
        )
    else:
        answers.update(explanation_correctness=None)

    if answers["explanation_correctness"] == "maybe":
        answers.update(
            explanation_maybe=questionary.select(
                "Why might the explanation be maybe correct?",
                choices=[
                    Choice(title="The programmer's intent is unclear", value="unclear"),
                    Choice(
                        title="The error is a one-sided conflict",
                        value="one-sided-conflict",
                    ),
                    Choice(title="Other (explain in notes)", value="other"),
                ],
            ).unsafe_ask()
        )
    else:
        answers.update(explanation_maybe=None)

    answers.update(
        fix=questionary.select(
            "Does it provide a fix?",
            choices=[
                Choice(
                    title="A specific fix is confidently provided", value="confident"
                ),
                Choice(
                    title="A fix or hint is given, but it is not asserted to be correct",
                    value="hint",
                ),
                Choice(title="A generic fix is provided", value="generic"),
                Choice(
                    title="A fix is implied or suggested", value="implicit-suggestion"
                ),
                Choice(title="No clear fix given", value="no"),
            ],
        ).unsafe_ask(),
    )

    if answers["fix"] != "no":
        answers.update(
            fix_correctness=questionary.select(
                "Is the fix correct?",
                choices=[
                    Choice(title="Yes", value="yes"),
                    Choice(
                        title="Maybe/Depends on programmer's intent/other",
                        value="maybe",
                    ),
                    Choice(title="No", value="no"),
                ],
            ).ask(),
        )
    else:
        answers.update(fix_correctness=None)

    answers.update(
        additional_errors=questionary.select(
            "Did it find additional errors?",
            choices=[
                Choice(title="Yes", value="yes"),
                Choice(title="Maybe", value="maybe"),
                Choice(title="No", value="no"),
            ],
        ).unsafe_ask(),
        notes=questionary.text(
            "(Optional) Any additional notes, thoughts, or other comments?",
        ).unsafe_ask(),
    )

    return answers


def by_unit(assignment):
    "Key function for grouping assignments by unit/scenario."
    srcml_path, version, _variant = assignment
    return srcml_path, version


### The script starts here ###

with open(HERE / "sample.pickle", "rb") as sample_file:
    _ALL_SCENARIOS = pickle.load(sample_file)

ALL_SCENARIOS = {
    (scenario["xml_filename"], scenario["version"]): scenario
    for scenario in _ALL_SCENARIOS
}

with open(HERE / "llm.pickle", "rb") as llm_file:
    LLM_RESULTS = pickle.load(llm_file)

GPT4_CODE_ONLY_RESPONSES = LLM_RESULTS["error_only"]
GPT4_CONTEXTUAL_RESPONSES = LLM_RESULTS["code_and_context"]

# Set up the database.
db = Database("answers.sqlite3")
answers_table = db["answers"].create(  # type: ignore
    {
        "srcml_path": str,
        # version looks like an int, but should be treated as a string:
        "version": str,
        # See Variant above
        "variant": str,
        # One of the raters, determined from the username
        "rater": str,
        # This will actually be stored as JSON. I know, that's terrible, but the
        # schema is too likely to change, so I'm going to make this future
        # Eddie's problem.
        "answers": str,
    },
    pk=("srcml_path", "version", "variant", "rater"),
    if_not_exists=True,
)

# Get rater's name from their username:
ALLOWED_USERS = ("eddie", "brett", "prajish")
username = os.environ.get("USER")
if username not in ALLOWED_USERS:
    rater = questionary.select("Who are you?", choices=ALLOWED_USERS).unsafe_ask()
else:
    rater = username

# Find all scenarios assigned to this rater.
assignments = set()
with open("assignments.tsv") as assignments_file:
    for line in assignments_file:
        _pem_category, srcml_path, version = line.strip().split("\t")
        for variant in ALL_VARIANTS:
            assignments.add((srcml_path, version, variant))

# Figure out which assignments need answers.
answered = set(
    db.execute(
        "SELECT srcml_path, version, variant FROM answers WHERE rater = ?", (rater,)
    ).fetchall()
)
needs_answers = assignments - answered

# Do the actual rating!
for (srcml_path, version), group in groupby(needs_answers, by_unit):
    variants_needed = [x[2] for x in group]
    scenario = ALL_SCENARIOS[(srcml_path, version)]
    try:
        ask_about_scenario(scenario, variants_needed)  # type: ignore
    except RaterQuitException:
        print("See you next time!")
        sys.exit(0)

print("You've done it! You have rated all the messages! 🎉")

# fetch all the of answers, create a set, then remove items from the assignments

## TODO: MESSY TESTING STUFF HERE:
# TODO: expand this for all scenarios
# scenario = [
#    s
#    for s in ALL_SCENARIOS
#    # This PEM is intersting because the ')' expected message makes very little sense:
#    if s["xml_filename"] == "/data/mini/srcml-2018-06/project-12826519/src-61952797.xml"
#    and s["version"] == "2495882730"
# ][0]
# import random
# i, scenario = random.choice(list(enumerate(ALL_SCENARIOS)))
# print(f"ALL_SCENARIOS[{i}]")
## ask_about_scenario(scenario, ["javac", "gpt-4-error-only", "gpt-4-with-context"])
# ask_about_scenario(scenario, ["gpt-4-error-only"])
# ask_about_scenario(ALL_SCENARIOS[0], ["javac"])
# print(ALL_SCENARIOS[0])
