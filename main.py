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
    sanitised_text TEXT,
    javac_name TEXT,

    PRIMARY KEY("srcml_path","version")
);
"""


def main():
    conn = sqlite3.connect("useful.sqlite3")

    conn.executescript(SCHEMA)
    conn.execute('ATTACH DATABASE "errors.sqlite3" AS original')

    # Adds sanitize_message() and javac_name() helpers
    register_helpers(conn)
    register_is_top_error(conn)

    with conn:
        conn.execute(
            """
            INSERT INTO messages
                SELECT srcml_path, version, start, end, text, sanitize_message(text), javac_name(text)
                FROM original.messages
                WHERE rank = 1
                  AND is_top_error(sanitize_message(text), javac_name(text))
            """
        )


if __name__ == "__main__":
    main()
