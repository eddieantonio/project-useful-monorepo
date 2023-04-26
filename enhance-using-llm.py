#!/usr/bin/env python3

"""
enhance-using-llm.py -- enhance error messages using an LLM.

REQUIREMENTS:
    sample.pickle

DESCRIPTION:
    This will use the OpenAI API to enhance error messages from the sample using
    an LLM. Currently, this uses GPT-4.
    NOTE: OpenAI API calls cost $$$, so don't go overboard running this script!
    To avoid hurting our bank account, this script actively avoids enhancing the
    same PEM twice. This is accomplished by storing the enhanced PEMs in a
    nested directory structure, and checking if the API call has already been
    issued before making it.

ENVIRONMENT VARIABLES:
    OPENAI_API_KEY -- a valid API key for OpenAI. Hint! Store this in the .env file!

OUTPUTS:
    llm/ -- directory with JSON files
        code-only/ -- NOTE! this should be called "error-only", but mistakes were made
            {n}-{message_id}.json
        code-and-context/
            {n}-{message_id}/
                {k}-{src}-{version}.json

SEE ALSO:
    pickle-llm-results.py -- pickle the directory structure in one easy-to-share file!
"""

import os
import sys
import pickle
import json
import logging
from pathlib import Path, PurePosixPath
from itertools import groupby

import openai
from dotenv import load_dotenv
from tqdm import tqdm

from blackbox_mini import JavaCompilerError

# Adapated from https://github.com/openai/openai-cookbook/blob/main/examples/How_to_format_inputs_to_ChatGPT_models.ipynb
# Intereting quote:
# > Best practices for instructing models may change from model version to model
# > version. The advice that follows applies to gpt-3.5-turbo-0301 and may not
# > apply to future models.
MODEL = "gpt-4"

# The maximum length of a prompt is 8192 tokens. Since we cannot reliably convert characters to tokens without yet another API call,
# I will arbitrarily set the maximum length to the size of the largest prompt that fit under the limit:
MAX_SOURCE_CODE_LENGTH = 13919

# API key should be stored in .env or otherwise passed in as an environment variable:
load_dotenv()

# Use API Key with the client
try:
    openai.api_key = os.environ["OPENAI_API_KEY"]
except KeyError:
    print("Forgot to set OPENAI_API_KEY environment variable")
    sys.exit(1)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


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
    ALL_SCENARIOS = pickle.load(f)

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
        enumerate(groupby(ALL_SCENARIOS, key=by_pem_category), start=1)
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
        be done in a single for loop, you don't want to see what that looks like!
        """
        for n, (category, group) in enumerate(
            groupby(ALL_SCENARIOS, key=by_pem_category), start=1
        ):
            for k, scenario in enumerate(group, start=1):
                yield n, k, category, scenario

    for n, k, category, scenario in tqdm(
        numbererd_scenarios(), total=len(ALL_SCENARIOS)
    ):
        code = scenario["unit"].source_code
        pem = scenario["unit"].pems[0]

        srcml_path = scenario["xml_filename"]
        version = scenario["version"]

        subdirectory_name = f"{n:02d}-{category}"
        subdirectory = CODE_AND_CONTEXT_DIR / subdirectory_name
        subdirectory.mkdir(exist_ok=True)

        base_srcml_name = PurePosixPath(srcml_path).stem
        json_path = subdirectory / f"{k:02d}-{base_srcml_name}-{version}.json"

        # Skip if we've already collected this response:
        if json_path.exists():
            continue

        # Skip source code contexts that are way too big:
        if len(code) > MAX_SOURCE_CODE_LENGTH:
            logger.warning(
                f"Skipping {json_path.stem} because it exceeds the maximum length of {MAX_SOURCE_CODE_LENGTH} tokens."
            )
            continue

        request = dict(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": make_prompt_with_context(code, pem)},
            ],
            temperature=0,
        )

        response = openai.ChatCompletion.create(**request)

        with json_path.open(mode="w") as json_file:
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
