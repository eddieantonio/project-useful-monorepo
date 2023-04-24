"""
rate-pems.py -- rate programming error messages

REQUIREMENTS:
    sample.pickle -- a sample of scenarios from Blackbox Mini

"""

# Let's load the error messages from the file.

import pickle

RED = "\x1b[31m"
BOLD = "\x1b[1m"
RESET = "\x1b[m"
GREY = "\x1b[38:5:243m"

with open("sample.pickle", "rb") as f:
    scenarios = pickle.load(f)

# TODO: expand this for all scenarios
scenario = scenarios[13]

unit = scenario["unit"]

# Use pygments to pretty-print the Java source code to the terminal.
from pygments import highlight
from pygments.lexers import JavaLexer
from pygments.formatters import TerminalFormatter

source_lines = highlight(
    unit.source_code, JavaLexer(), TerminalFormatter()
).splitlines()

# Place a gutter on the side of the source code
biggest_line_no_width = len(str(len(source_lines)))

assert len(unit.pems) >= 1, f"There should be at least one PEM, but found {unit.pems!r}"
pem = unit.pems[0]
pem_line_no = pem.start.line

for line_no, line in enumerate(source_lines, start=1):
    on_pem_line = line_no == pem_line_no

    if not on_pem_line:
        print(f"{line_no:>{biggest_line_no_width}} | {line}")
        continue

    # Priting the error message:
    print(f"{RED}{pem!s}{RESET}")
    print(f"{BOLD}{RED}{line_no:>{biggest_line_no_width}}{RESET} | {line}")

    # columns are 1-indexed (annoyingly):
    padding = (pem.start.column - 1) * " "
    margin = " " * biggest_line_no_width

    if pem.start.line == pem.end.line:
        marker = "^" * max(1, pem.end.column - pem.start.column)
    else:
        marker = "^"
    print(f"{margin} | {padding}{RED}{marker}{RESET}")
    print(f"{margin} |")
