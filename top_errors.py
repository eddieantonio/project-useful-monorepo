"""
Creates a new SQLite3 function that will return 1 (true) if an error messages is a
**top** error message. The top error messages have been precomputed on the orignal
database using this query:

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

import sqlite3

TOP_JAVAC_NAMES = {
    "compiler.err.premature.eof",
    "compiler.err.cant.resolve",
    "compiler.err.illegal.start.of.expr",
    "compiler.err.cant.resolve",
    "compiler.err.cant.resolve",
    "compiler.err.not.stmt",
    "compiler.err.prob.found.req",
    "compiler.err.missing.ret.stmt",
    "compiler.err.cant.apply.symbol",
    "compiler.err.invalid.meth.decl.ret.type.req",
    "compiler.err.doesnt.exist",
    "compiler.err.illegal.start.of.type",
    "compiler.err.unclosed.str.lit",
    "compiler.err.already.defined",
    "compiler.err.illegal.start.of.stmt",
}

TOP_EXPECTED_ERRORS = {
    "';' expected",
    "<identifier> expected",
    "class, interface, or enum expected" "')' expected",
    "'(' expected",
}


def is_top_error(
    sanitized_message: str,
    javac_name: str,
    _TOP_JAVAC_NAMES=TOP_JAVAC_NAMES,
    _TOP_EXPECTED_ERRORS=TOP_EXPECTED_ERRORS,
) -> bool:
    """
    Intended to be registered as an SQLite3 function.
    """
    return javac_name in _TOP_JAVAC_NAMES or sanitized_message in _TOP_EXPECTED_ERRORS


def register_is_top_error(conn: sqlite3.Connection):
    """
    Registers is_top_error(message, javac_name) for use with the given SQLite3 connection.
    """
    conn.create_function("is_top_error", 2, is_top_error)
