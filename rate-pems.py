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

SEE ALSO
    pickle-sample.py -- creates sample.pickle
    pickle-llm-results.py -- creates llm.pickle
"""

import sys
import pickle
from typing import Literal, Sequence
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

from blackbox_mini import JavaUnit

# Rich console for pretty-printing:
console = Console()
console.width = min(120, console.width)

# Configure the JavaLexer so that it does not eat up empty lines!
java_lexer = JavaLexer(stripnl=False)
terminal_formatter = TerminalFormatter()

Configuration = Literal["javac", "gpt-4-error-only", "gpt-4-with-context", "decaf"]

HERE = Path(__file__).parent.resolve()


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


with open(HERE / "sample.pickle", "rb") as f:
    ALL_SCENARIOS = pickle.load(f)

with open(HERE / "llm.pickle", "rb") as f:
    LLM_RESULTS = pickle.load(f)

GPT4_CODE_ONLY_RESPONSES = LLM_RESULTS["error_only"]
GPT4_CONTEXTUAL_RESPONSES = LLM_RESULTS["code_and_context"]


def print_source_code(scenario):
    unit = scenario["unit"]

    # Fence off the source code:
    console.rule("[bold]Source code")
    print_with_javac_pem(unit)


def ask_about_scenario(scenario, configurations: Sequence[Configuration]):
    """
    Asks the user to rate a scenario under various different configurations.

    A scenario is some erroneous Java code, and a programming error message.
    A configuration is one of the following:
     - javac (control)
     - gpt-4-error-only -- enhance only the error message text
     - gpt-4-with-context -- enhance the error message text with code context
     - decaf -- (not yet implemented!)
    """
    print_source_code(scenario)

    for configuration in configurations:
        print()
        ask_about_configuration(scenario, configuration)


def ask_about_configuration(scenario, configuration: Configuration):
    unit = scenario["unit"]

    console.rule(
        f"[bold]Rate this {configuration} error message for the above context[/bold]:"
    )
    if configuration == "javac":
        javac_error_message = unit.pems[0].fixed_error_message_text
        length = len(javac_error_message)
        print(javac_error_message)
    elif configuration == "gpt-4-error-only":
        message = GPT4_CODE_ONLY_RESPONSES[scenario["pem_category"]]
        length = len(message)
        md = Markdown(message)
        console.print(md)
    elif configuration == "gpt-4-with-context":
        message = GPT4_CONTEXTUAL_RESPONSES.get(
            # I know, I know, it should be "srcml_path", but I accidentally
            # changed it to "xml_filename" in the pickle, so here we are:
            (scenario["xml_filename"], scenario["version"])
        )
        if message is None:
            # TODO: what to do about messages that don't have a response?
            raise NotImplementedError(
                "The source code is too big to get a response from GPT-4"
            )
        length = len(message)
        md = Markdown(message)
        console.print(md)
    elif configuration == "decaf":
        raise NotImplementedError("Don't have Decaf PEMs yet")
    else:
        raise ValueError(f"Unknown configuration: {configuration!r}")

    console.rule()

    try:
        answers = ask_questions_for_current_configuration()
        answers.update(length=length)
    except KeyboardInterrupt:
        print()
        print("Exiting...")
        sys.exit(1)
    print(answers)


def ask_questions_for_current_configuration():
    answers = {}

    # Denny et al. 2021 CHI paper readability factors
    answers.update(
        jargon=questionary.text(
            "How many jargon words are in this message?",
            validate=NonNegativeNumberValidator,
        ).unsafe_ask(),
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
                Choice(title="A fix is confidently provided", value="confident"),
                Choice(
                    title="A fix or hint is given, but it is not asserted to be correct",
                    value="hint",
                ),
                Choice(title="A fix is implied/suggested", value="implicit-suggestion"),
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


# TODO: expand this for all scenarios
scenario = [
    s
    for s in ALL_SCENARIOS
    # This PEM is intersting because the ')' expected message makes very little sense:
    if s["xml_filename"] == "/data/mini/srcml-2018-06/project-12826519/src-61952797.xml"
    and s["version"] == "2495882730"
][0]
ask_about_scenario(scenario, ["javac", "gpt-4-error-only", "gpt-4-with-context"])
