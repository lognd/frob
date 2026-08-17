"""Bump the patch version in pyproject.toml unconditionally.

Prints the new version to stdout. T-2242: this is now a thin CLI wrapper
over `frob.release.bump_patch_version` -- the canonical implementation
lives there so `frob release publish` can call it directly (a Python
function call, not a subprocess spawn of this script). Run via `uv run
python scripts/bump_version.py` (never bare `python3` -- T-2236: this
machine's `python3` is 3.10, the project requires >=3.11), which makes
`frob` importable since it's installed editable into the same venv.
"""

import sys
from pathlib import Path

from frob.release import bump_patch_version

result = bump_patch_version(Path("."))
if result.is_err:
    print(f"bump_version: {result.danger_err}", file=sys.stderr)
    sys.exit(1)

new = result.danger_ok
print(f"bumped -> {new}", file=sys.stderr)
print(new)
