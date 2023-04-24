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
            {n}-{message_id}/
                {k}-{src}-{version}.json
"""

import json
import os
import pickle
import sys
from itertools import groupby
from pathlib import Path, PurePosixPath

import openai
from dotenv import load_dotenv
from tqdm import tqdm

from blackbox_mini import JavaCompilerError

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
HERE = Path(__file__).parent.resolve()
LLM_DIR = HERE / "llm"
LLM_DIR.mkdir(exist_ok=True)
CODE_ONLY_DIR = LLM_DIR / "code-only"
CODE_ONLY_DIR.mkdir(exist_ok=True)
CODE_AND_CONTEXT_DIR = LLM_DIR / "code-and-context"
CODE_AND_CONTEXT_DIR.mkdir(exist_ok=True)


def by_pem_category(scenario):
    return scenario["pem_category"]


def collect_error_only_responses() -> None:
    """
    Collect resposnes from OpenAI for **JUST** the error messages.

    This requires far fewer API calls than collecting responses for the code and context.
    """
    for n, (category, group) in tqdm(
        enumerate(groupby(scenarios, key=by_pem_category), start=1)
    ):
        json_filename = f"{n:02d}-{category}.json"
        scenario = next(group)
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

        with open(CODE_ONLY_DIR / json_filename, "w") as json_file:
            # Provide enough information to reconstruct the original scenario:
            json.dump(
                dict(
                    type="code-and-context",
                    # Although these results are (sort of) independent of the exact source file and error,
                    # it's useful to know exactly which file induced this error, particularly for the
                    # error messages that have an identifier in them, e.g., cannot find symbol  -  variable foo
                    srcml_path=srcml_path,
                    version=version,
                    pem_category=category,
                    request=request,
                    response=response.to_dict(),
                ),
                json_file,
            )


def collect_code_and_context_responses() -> None:
    """
    Collect responses from OpenAI for the code and context.
    """

    def numbererd_scenarios():
        """
        Yield all scenarios. Each scenario includes its error message category,
        its rank (n) and the scenario's index within its category (k).

        I factored this out as a generator, because, although this could all
        be done in one for loop, you don't want to see what that looks like!
        """
        for n, (category, group) in enumerate(
            groupby(scenarios, key=by_pem_category), start=1
        ):
            for k, scenario in enumerate(group, start=1):
                yield n, k, category, scenario

    for n, k, category, scenario in tqdm(numbererd_scenarios(), total=len(scenarios)):
        code = scenario["unit"].source_code
        pem = scenario["unit"].pems[0]

        srcml_path = scenario["xml_filename"]
        version = scenario["version"]
        subdirectory_name = f"{n:02d}-{category}"
        base_srcml_name = PurePosixPath(srcml_path).stem
        json_filename = f"{k:02d}-{base_srcml_name}-{version}.json"

        request = dict(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": make_prompt_with_context(code, pem)},
            ],
            temperature=0,
        )

        subdirectory = CODE_AND_CONTEXT_DIR / subdirectory_name
        subdirectory.mkdir(exist_ok=True)

        response = openai.ChatCompletion.create(**request)

        with open(subdirectory / json_filename, "w") as json_file:
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
                json_file,
            )


# Collect responses for code-only prompts
# When the marker exists, we assume that the responses have already been collected.
marker = CODE_ONLY_DIR / ".finished-querying"
if not marker.exists():
    collect_error_only_responses()
    marker.touch()

# Collect responses for code and context prompts
collect_code_and_context_responses()
# TODO: use sets to confirm which scenarios have been completed and which still need to be queried.
