"""
Create a useful subset from errors.sqlite3 (collected during Project Antipatterns).

This subset contains only the top 20 "first" programming error messages in Blackbox
Mini.
"""

import sqlite3

from project_antipatterns.enrich_database import register_helpers
from top_errors import register_is_top_error

SCHEMA = """
CREATE TABLE messages(
    srcml_path TEXT,
    version INT,
    start TEXT,
    end TEXT,
    text TEXT,
    sanitized_text TEXT,
    javac_name TEXT,

    PRIMARY KEY(srcml_path, version)
);

CREATE TABLE top_messages(
    rank INT,
    identifier TEXT,

    PRIMARY KEY(identifier)
);
"""

# Top first error messages (see query below)
TOP_ERRORS = [
    (1, "compiler.err.premature.eof"),
    (2, "';' expected"),
    (3, "compiler.err.cant.resolve[variable]"),
    (4, "compiler.err.illegal.start.of.expr"),
    (5, "<identifier> expected"),
    (6, "compiler.err.cant.resolve[method]"),
    (7, "compiler.err.cant.resolve[class]"),
    (8, "compiler.err.not.stmt"),
    (9, "class, interface, or enum expected"),
    (10, "')' expected"),
    (11, "compiler.err.prob.found.req"),
    (12, "compiler.err.missing.ret.stmt"),
    (13, "compiler.err.cant.apply.symbol"),
    (14, "compiler.err.invalid.meth.decl.ret.type.req"),
    (15, "compiler.err.doesnt.exist"),
    (16, "compiler.err.illegal.start.of.type"),
    (17, "compiler.err.unclosed.str.lit"),
    (18, "'(' expected"),
    (19, "compiler.err.already.defined[variable]"),
    (20, "compiler.err.illegal.start.of.stmt"),
]

# How to obtain the top error messages. Note: we don't run this query because it takes forever,
# so I hard-coded the results above.
TOP_ERRORS_QUERY = """
SELECT sanitized_text,
       coalesce(javac_name, sanitized_text) as identifier,
       COUNT(sanitized_text) AS occurrences,
       javac_name,
       100.0 * COUNT(sanitized_text) / (SELECT COUNT(*) FROM messages WHERE rank = 1) as percentage,
       SUM(100.0 * COUNT(sanitized_text) / (SELECT COUNT(*) FROM messages WHERE rank = 1)) OVER
          (ORDER BY COUNT(sanitized_text) DESC) as cummulative_percentage
  FROM messages JOIN sanitized_messages USING (text)
 WHERE rank = 1
 GROUP BY sanitized_text
 ORDER BY COUNT(sanitized_text) DESC
 LIMIT 20;
"""


def main():
    conn = sqlite3.connect("useful.sqlite3")
    conn.executescript(SCHEMA)

    with conn:
        conn.executemany(
            "INSERT INTO top_messages VALUES (?, ?)",
            TOP_ERRORS,
        )

    conn.execute('ATTACH DATABASE "errors.sqlite3" AS original')

    # Adds sanitize_message() and javac_name() helpers
    register_helpers(conn)
    register_is_top_error(conn)

    with conn:
        # INSERT OR IGNORE because there is ONE duplicate srcml_path, version pair
        # Namely /data/mini/srcml-2013-06/project-4425/src-12277.xml version 209269
        conn.execute(
            """
            INSERT OR IGNORE INTO messages
                SELECT srcml_path, version, start, end, text, sanitize_message(text), javac_name(text)
                FROM original.messages JOIN top_messages
                  ON top_messages.identifier = COALESCE(parameterized_javac_name(text), sanitize_message(text))
               WHERE original.messages.rank = 1
            """
        )

    # Make sure we actually have the error messages we wanted.
    distinct_messages = conn.execute(
        "SELECT COUNT(DISTINCT sanitized_text) FROM messages"
    ).fetchone()[0]
    assert distinct_messages == len(TOP_ERRORS)


if __name__ == "__main__":
    main()
