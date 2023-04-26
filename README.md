# Project Useful Monorepo

All my scripts and things for Project Useful. The cryptic title is half
for fun, and half because I lack creativity.

This borrows from the data collected from [project-antipatterns].

Note: **PEM** = **Programming Error Message**

# Requirements

 - Python 3.8+. I use Python 3.8 on white and Python 3.11 on my own
   laptop.
 - Poetry

# Install

**NOTE**: This step can be skipped if running the data collection code on the Blackbox server.

    $ poetry install

The only scripts that **require** external Python dependencies (and hence, require the above step) are:

 - `enhance-using-llms.py`
 - `rate-pems.py`

# Utilities

## Blackbox Mini

These files allow you to explore the data in Blackbox Mini. These should
be run on `white.bluej.org`:

 * `bbm-list` -- list versions of a file in Blackbox Mini
 * `bbm-view` -- show a file at a particular version in Blackbox Mini

## Data collection

NOTE: You will need to obtain `errors.sqlite3` separately, as this was
collected during [project-antipatterns].

 * `create-useful-database.py` -- reads `errors.sqlite3` and creates
   a new database of "eligible" programming error messages
 * `create-pem-index.py` -- reads `useful.sqlite3` and creates an index
   from programming error message category to the files/versions that
   induce that PEM.
 * `sample-pem-index.py` -- reads `pem-index.pickle` and prints a small
   sample of files/versions that induce a PEM category.
   This sample can be interpreted as a TSV file.
 - `pickle-sample.py` -- reads `sample.tsv` and collects source code and PEMs
   for all of the scenarios and stores them in `sample.pickle`.
    **This file must be run on the Blackbox server!**
 - `enhance-using-llm.py` -- reads `sample.pickle` and enhances the error
    messages using the OpenAI API. **This script costs you money!**
    The output is a messy directory structure called `llm/`.
 - `pickle-llm-results.py` -- takes the `llm/` directory structure,
   and creates `llm.pickle`, which is a much more easy-to-use version
   of the same information.

# Interactive scripts

 - `rate-pems.py` is an interactive TUI application, intended to collect
   judgements about PEM quality.
  

# Other info

I have copy-pasted a few files from [project-antipatterns], which is in
the `project_antipatterns` package.

[project-antipatterns]: https://github.com/eddieantonio/project-antipatterns

# Glossary

 - **scenario**: a _unit_ with at least one programming error message
   produced by `javac`.
 - **unit**: a Java source code file at a particular version
 - **sample**: a random sample of eligible scenarios
 - **PEM category**: a collection of clustered programming error messages.
   These somewhat correspond to the javac's internal error IDs, however there
   some of these IDs have been broken down into multiple categories.

# Copyright

All code Copyright © 2022, 2023 Eddie Antonio Santos. AGPL-3.0 Licensed.
