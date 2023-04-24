from __future__ import annotations

from dataclasses import dataclass


@dataclass
class JavaCompilerError:
    "A programming error message, as recorded by BlueJ and javac"
    filename: str
    text: str
    start: Position
    end: Position

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
    "A position in the source code file."
    line: int
    column: int

    @classmethod
    def from_attribute(cls, attribute: str) -> Position:
        "Parse a position from either an start='' or end='' XML attribute."
        return cls(*(int(x) for x in attribute.split(":")))
