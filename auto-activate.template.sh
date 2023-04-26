#!/bin/bash

# Automatically activates the virtual environment and executes rate-pems.py
# This script should be customized before deploying.
# In particular, note where the virtual environment is located!

# Suggestion: instruct poetry to install the virtual environment in the project directory using:
# $ poetry config virtualenvs.in-project true
# $ poetry install --no-root --only main --compile 

# I was fighting with GitHub Copilot, and it kept suggesting this line -- I usually use:
# $(realpath $(dirname $0)) -- however, the pwd -P trick does the same thing, and is more portable.
# Note: in the actual script, I recommend just hardcoding the path ¯\_(ツ)_/¯
SCRIPTPATH="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
# TODO: replace this with YOUR path to the virtual environment.  You can find it by running:
VENV="$(poetry env info --path)"
# Turns out that "source" is a feature that is not available in ordinary Bourne shell.
source "$VENV/bin/activate"

exec python3 $SCRIPTPATH/rate-pems.py "$@"
