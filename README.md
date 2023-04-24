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

**NOTE**: You only need to install requirements for development. As of
now (2023-04-20), there is no need to install any additional Python
requirements to collect data.

    $ poetry install

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
   sample of files/versions that induce a PEM category
 - `pickle-sample.py` 

# Other info

I have copy-pasted a few files from [project-antipatterns], which is in
the `project_antipatterns` package.

[project-antipatterns]: https://github.com/eddieantonio/project-antipatterns

# Glossary

 - **scenario**: a _unit_ with at least one programming error message
   produced by `javac`.
 - **unit**: a Java source code file at a particular version
 - **sample**: a random sample of eligible scenarios

# Copyright

All code Copyright © 2022, 2023 Eddie Antonio Santos. AGPL-3.0 Licensed.
