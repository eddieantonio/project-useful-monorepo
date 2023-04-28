"""
I accidentally used the wrong name for "type" consisetently in the JSONs, so I need to those here.

{"type": "code-and-context"} should be "error-only"
{"type": "code-only"} should be "error-with-context"
"""

import json
import shutil
from pathlib import Path

HERE = Path(__file__).parent.resolve()
LLM_DIR = HERE / "llm"
ERROR_ONLY_DIR = LLM_DIR / "code-only"

# Fix "code-and-context" to "error-only"
for json_path in ERROR_ONLY_DIR.glob("**/*.json"):
    # Create a backup first
    backup_path = json_path.with_name(json_path.name + ".bak")
    shutil.copy(json_path, backup_path)

    with open(json_path, "r") as f:
        data = json.load(f)
    data["type"] = "error-only"
    with open(json_path, "w") as f:
        json.dump(data, f)

ERROR_WITH_CONTEXT = LLM_DIR / "code-and-context"

# Fix "code-only" to "error-with-context"
for json_path in ERROR_ONLY_DIR.glob("**/*.json"):
    # Create a backup first
    backup_path = json_path.with_name(json_path.name + ".bak")
    shutil.copy(json_path, backup_path)
    with open(json_path, "r") as f:
        data = json.load(f)
    data["type"] = "error-with-context"
    with open(json_path, "w") as f:
        json.dump(data, f)
