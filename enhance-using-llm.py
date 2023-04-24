#!/usr/bin/env python3

"""
enhance-using-llm.py -- enhance error messages using an LLM.

REQUIREMENTS:
    sample.pickle

OUTPUTS:
    llm/ directory with JSON files

    llm/
        code-only/
            {n}-{message_id}.json
        code-and-context/
            {n}-{message_id}.json
"""

import os
import sys
import pickle
import json
from pathlib import Path
from itertools import groupby

import openai
from dotenv import load_dotenv
from tqdm import tqdm

from blackbox_mini import JavaCompilerError

here = Path(__file__).parent.resolve()

# API key should be stored in .env or otherwise passed in as an environment variable:
load_dotenv()

# Use API Key with the client
try:
    openai.api_key = os.environ["OPENAI_API_KEY"]
except KeyError:
    print("Forgot to set OPENAI_API_KEY environment variable")
    sys.exit(1)

# Adapated from https://github.com/openai/openai-cookbook/blob/main/examples/How_to_format_inputs_to_ChatGPT_models.ipynb
# Intereting quote:
# > Best practices for instructing models may change from model version to model
# > version. The advice that follows applies to gpt-3.5-turbo-0301 and may not
# > apply to future models.
MODEL = "gpt-4"


def make_prompt_with_context(code: str, error: JavaCompilerError) -> str:
    """
    Uses the prompt from Leinonen et al. 2022, Prompt 3.2.1 to enhance an error message.
    """

    return (
        "Code:\n"
        "```\n"
        f"{code}\n"
        "```\n"
        "\n"
        "Output:\n"
        "```\n"
        f"{error!s}\n"
        "```\n"
        "Plain English explanation of why running the above code causes an error and how to fix the problem"
    )


def make_prompt_for_error(error: JavaCompilerError) -> str:
    """
    Creates a prompt only for the Java error message.
    """

    return f"Plain English explanation of this error message: {error.text}"


with open("sample.pickle", "rb") as f:
    scenarios = pickle.load(f)

# Ensure the directory structure exists:
LLM_DIR = here / "llm"
LLM_DIR.mkdir(exist_ok=True)
CODE_ONLY_DIR = LLM_DIR / "code-only"
CODE_ONLY_DIR.mkdir(exist_ok=True)

for n, (category, group) in tqdm(
    enumerate(groupby(scenarios, key=lambda s: s["pem_category"]), start=1)
):
    scenario = next(group)
    code = scenario["unit"].source_code
    pem = scenario["unit"].pems[0]
    # Annoyingly, I started calling the scrml_path "xml_filename" while creating a sample:
    srcml_path = scenario["xml_filename"]
    version = scenario["version"]

    request = dict(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": make_prompt_for_error(pem)},
        ],
        temperature=0,
    )
    response = openai.ChatCompletion.create(**request)

    with open(CODE_ONLY_DIR / f"{n}-{category}.json", "w") as f:
        # Provide enough information to reconstruct the original scenario:
        json.dump(
            dict(
                type="code-only",
                # Although these results are (sort of) independent of the exact source file and error,
                # it's useful to know exactly which file induced this error, particularly for the
                # error messages that have an identifier in them, e.g., cannot find symbol  -  variable foo
                srcml_path=srcml_path,
                version=version,
                pem_category=category,
                request=request,
                response=response.to_dict(),
            ),
            f,
        )


sys.exit(0)

with open("javac-error.pickle", "wb") as f:
    pickle.dump(response, f)

with open("sample.pickle", "rb") as f:
    scenarios = pickle.load(f)

message_templates = {s["pem_category"] for s in scenarios}
#

# TODO: store in some kind of database
