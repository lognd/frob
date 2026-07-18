"""
Bump the patch version in pyproject.toml unconditionally.
Prints the new version to stdout. Edits pyproject.toml in place.
"""

import re
import sys
import tomllib
from pathlib import Path

#: This script's own target file; never imported elsewhere.
_PYPROJECT = Path("pyproject.toml")

with _PYPROJECT.open("rb") as f:
    data = tomllib.load(f)

current = data["project"]["version"]
parts = current.split(".")
parts[-1] = str(int(parts[-1]) + 1)
new = ".".join(parts)

text = _PYPROJECT.read_text()
text = re.sub(r'^version = "[^"]+"', f'version = "{new}"', text, flags=re.M)
_PYPROJECT.write_text(text)

print(f"bumped {current} -> {new}", file=sys.stderr)
print(new)
