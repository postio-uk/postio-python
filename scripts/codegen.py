#!/usr/bin/env python3
"""Regenerate ``postio/_models.py`` from the live OpenAPI spec.

Pulls https://postio.co.uk/openapi.json, runs datamodel-code-generator into
``postio/_models.py``, then prints a reminder about manual patches that need
to be reapplied.

Usage:

    uv run python scripts/codegen.py
    uv run python scripts/codegen.py --spec /path/to/openapi.json
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

SPEC_URL = "https://postio.co.uk/openapi.json"
REPO = Path(__file__).resolve().parent.parent
TARGET = REPO / "postio" / "_models.py"

# Manual patches that must survive every regen. Keep this list in sync with
# the comments in ``_models.py``. Each patch is described as:
#   1. The runtime drift it papers over.
#   2. The exact change to make.
PATCHES_REMINDER = """
After every regen, reapply these manual patches in postio/_models.py:

  PhoneResult — spec marks every nullable field as `required` and the API
                drops them on invalid input. Add `= None` defaults to every
                str | None / bool | None field (number, isValid, isPossible
                stay required). Also: change `isReachable: str | None` to
                `isReachable: bool | str | None = None` because the live
                API returns booleans there.

If postio-api ever ships a spec/runtime alignment, drop the patches and let
the regen drive the model verbatim.
"""


def fetch_spec(dest: Path, source: str) -> None:
    if source.startswith(("http://", "https://")):
        print(f"fetching spec from {source}")
        urllib.request.urlretrieve(source, dest)  # noqa: S310 (spec is our own)
    else:
        print(f"reading spec from {source}")
        shutil.copyfile(source, dest)


def run_codegen(spec: Path, out: Path) -> None:
    cmd = [
        "uv",
        "run",
        "datamodel-codegen",
        "--input",
        str(spec),
        "--input-file-type",
        "openapi",
        "--output",
        str(out),
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--target-python-version",
        "3.10",
        "--use-standard-collections",
        "--use-union-operator",
        "--use-schema-description",
        "--field-constraints",
        "--collapse-root-models",
    ]
    print("running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", default=SPEC_URL, help="OpenAPI spec URL or path")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        spec_path = tmpdir / "openapi.json"
        fetch_spec(spec_path, args.spec)
        run_codegen(spec_path, TARGET)

    print(f"\nwrote {TARGET}")
    print(PATCHES_REMINDER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
