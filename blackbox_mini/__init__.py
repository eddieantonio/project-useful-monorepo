"""
Utilities for interacting with Blackbox Mini.
"""

from __future__ import annotations

import copy
import os
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from functools import cached_property
from typing import List

# Unknown filename.
UNKNOWN = "<unknown>"

# TODO: get rid of this constant:
MAX_ERRORS = 1


@dataclass
class JavaUnit:
    unit: ET.Element
    filename: str
    pems: List[JavaCompilerError]

    @staticmethod
    def from_path_and_version(srcml_path: os.PathLike, version: str) -> JavaUnit:
        """
        Return a Java unit from its srcml path and version.
        """
        root = ET.parse(os.fspath(srcml_path)).getroot()
        unit = find_requested_version(root, version)

        filename = determine_file_name(unit)

        # Get rid of the compiler errors, but add them to our data structure.
        pems = []
        for pem_element in unit.findall("./compile-error"):
            pems.append(JavaCompilerError.from_element(pem_element, filename))
            unit.remove(pem_element)

        return JavaUnit(unit=unit, filename=filename, pems=pems)

    @cached_property
    def source_code(self) -> str:
        # Need to add empty lines before the first actual line number in the file, or else the
        # line numbering will be off.
        first_line_number = determine_first_line_number(self.unit)
        preceding_empty_lines = "\n" * (first_line_number - 1)

        source_code = preceding_empty_lines + "".join(self.unit.itertext())
        return source_code


@dataclass
class JavaCompilerError:
    """
    A programming error message, as recorded by BlueJ and javac.
    """

    filename: str
    text: str
    start: Position
    end: Position

    def __str__(self) -> str:
        return f"{self.filename}:{self.start.line}: error: {self.text}"

    @property
    def fixed_error_message_text(self) -> str:
        r"""
        There's a bug in Blackbox Mini where \n are literally encoded in the XML.
        This will return the error message text with the \n's replaced with newlines.
        """
        return self.text.replace("\\n", "\n")

    @classmethod
    def from_element(cls, element, filename: str = "<unknown>") -> JavaCompilerError:
        "Parse an compiler error from a <compile-error> XML element."
        return cls(
            text=element.text,
            filename=filename,
            start=Position.from_attribute(element.attrib["start"]),
            end=Position.from_attribute(element.attrib["end"]),
        )


@dataclass
class Position:
    """
    A position in the source code file.
    """

    line: int
    column: int

    @classmethod
    def from_attribute(cls, attribute: str) -> Position:
        "Parse a position from either an start='' or end='' XML attribute."
        return cls(*(int(x) for x in attribute.split(":")))


def find_requested_version(root, version: str):
    versions_available = []

    for unit in root.findall("./unit"):
        unit_version = unit.attrib["version"]
        if version == unit_version:
            return unit
        versions_available.append(unit_version)

    # TODO: return a module internal error for this:
    raise KeyError(
        f"Could not find version {version}. Versions available: {versions_available}"
    )


def determine_first_line_number(unit):
    try:
        first_element = next(iter(unit))
    except StopIteration:
        # The file is empty. Just pretend the file starts on line 1.
        return 1

    return Position.from_attribute(first_element.attrib["start"]).line


def determine_file_name(unit):
    "Figure out what the source code filename is."
    class_name_element = unit.find("./class/name")

    # No class name -- unable to determine the filename.
    if class_name_element is None:
        return UNKNOWN

    if class_name_element.text is not None:
        class_name = class_name_element.text
    else:
        # This might be a generic like Class<Name>. In which case, there will be a nexted name:
        base_name_element = class_name_element.find("./name")
        if base_name_element is None:
            # I don't know what this is:
            return UNKNOWN

        assert base_name_element.text is not None
        class_name = base_name_element.text

    # <name>ClassName </name> includes whitespace, so get rid of it:
    class_name = class_name.strip()
    return f"{class_name}.java"


def show_file(filename: str, version: str):
    root = ET.parse(filename).getroot()
    unit = find_requested_version(root, version)
    unit_with_compiler_errors = copy.deepcopy(unit)
    filename = determine_file_name(unit)

    # Get rid of the compiler errors from the version we want to print:
    for pem in unit.findall("./compile-error"):
        unit.remove(pem)

    pems_per_line = defaultdict(list)

    # Group PEMs per each source line of code that they're on
    pems_seen = 0
    pems = unit_with_compiler_errors.findall("./compile-error")
    for pem_element in pems:
        pem = JavaCompilerError.from_element(pem_element, filename)
        pems_per_line[pem.start.line].append(pem)
        pems_seen += 1
        if pems_seen >= MAX_ERRORS:
            break

    # Need to add empty lines before the first actual line number in the file, or else the
    # line numbering will be off.
    first_line_number = determine_first_line_number(unit)
    preceding_empty_lines = [""] * (first_line_number - 1)

    source_code = "".join(unit.itertext())
    source_lines = preceding_empty_lines + source_code.splitlines()

    biggest_line_no_width = len(str(len(source_lines)))

    for line_no, line in enumerate(source_lines, start=1):
        pems = pems_per_line.get(line_no)
        if pems is not None:
            pem = pems[0]
        else:
            pem = None

        if pem:
            pem.print()

        print(f"{line_no:>{biggest_line_no_width}} | {line}")

        if not pem:
            continue

        # columns are 1-indexed (annoyingly):
        padding = (pem.start.column - 1) * " "
        margin = " " * biggest_line_no_width

        if pem.start.line == pem.end.line:
            marker = "^" * max(1, pem.end.column - pem.start.column)
        else:
            marker = "^"
        print(f"{margin} | {padding}{marker}")
        print(f"{margin} |")


def get_source_code(xml_filename: str, version: str):
    """
    Gets the source code for a filename and version from Blackbox mini.
    """
    root = ET.parse(xml_filename).getroot()
    unit = find_requested_version(root, version)
    unit_with_compiler_errors = copy.deepcopy(unit)
    filename = determine_file_name(unit)

    # Get rid of the compiler errors from the version we want to print:
    for pem in unit.findall("./compile-error"):
        unit.remove(pem)

    # Need to add empty lines before the first actual line number in the file, or else the
    # line numbering will be off.
    first_line_number = determine_first_line_number(unit)
    preceding_empty_lines = [""] * (first_line_number - 1)

    source_code = "".join(unit.itertext())
    return source_code, filename
