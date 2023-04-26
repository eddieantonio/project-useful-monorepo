#!/usr/bin/env python3

"""
pickle-llm-results.py -- pickles data gathered from GPT-4

SYNOPSIS
    pickle-llm-results.py

REQUIREMENTS:
   llm/ and all its subdirectories, and JSON files.

DESCRIPTION:
    This will recursively walk llm/ and combine all the JSON into a file that is
    indexed by PEM category and scenario.

OUTPUT:
    llm.pickle -- a pickle of a dictionary containing the following keys:
        code_only -- a dictionary mapping PEM category to an enhanced PEM
        code_and_context -- a dictionary mapping (srcml_path, version) to an enhanced PEM
        _raw -- the raw JSON data

SEE ALSO:
    enhance-using-llms.py -- uses the OpenAI API to enhance PEMs
"""

import json
import pickle
from pathlib import Path

# Where we can find the data:
HERE = Path(__file__).parent
CODE_ONLY = HERE / "llm" / "code-only"
CODE_AND_CONTEXT_ONLY = HERE / "llm" / "code-and-context"

# We will store the full JSON in a dictionary, but for the purposes of rating
# PEMs, this data is superfluous.
raw = {
    "code_only": {},
    "code_and_context": {},
}

# Load the GPT-4 (code-only) error messages:
# This maps PEM category to plain text (which can be interpreted as Markdown)
code_only_messages = {}

for json_path in CODE_ONLY.glob("*.json"):
    with json_path.open() as json_file:
        data = json.load(json_file)

    pem_category = data["pem_category"]
    text = data["response"]["choices"][0]["message"]["content"]

    raw["code_only"][pem_category] = data
    code_only_messages[pem_category] = text

# Load GPT-4 (code and context) error messages:
# This maps (srcml_path, version) to plain text (which can be interpreted as Markdown)
code_and_data_messages = {}
for json_path in CODE_AND_CONTEXT_ONLY.glob("**/*.json"):
    with json_path.open() as json_file:
        data = json.load(json_file)

    srcml_path = data["srcml_path"]
    version = data["version"]
    text = data["response"]["choices"][0]["message"]["content"]

    raw["code_and_context"][(srcml_path, version)] = data
    code_and_data_messages[(srcml_path, version)] = text

# Pickle it!
with open("llm.pickle", "wb") as f:
    pickle.dump(
        {
            "code_only": code_only_messages,
            "code_and_context": code_and_data_messages,
            "_raw": raw,
        },
        f,
    )
