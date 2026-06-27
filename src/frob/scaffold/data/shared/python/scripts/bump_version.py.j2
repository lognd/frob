"""
Bump the patch version in pyproject.toml unconditionally.
Prints the new version to stdout. Edits pyproject.toml in place.
"""

import re
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        import toml as tomllib  # type: ignore[no-redef,import-not-found]

PYPROJECT = Path("pyproject.toml")

with PYPROJECT.open("rb") as f:
    data = tomllib.load(f)

current = data["project"]["version"]
parts = current.split(".")
parts[-1] = str(int(parts[-1]) + 1)
new = ".".join(parts)

text = PYPROJECT.read_text()
text = re.sub(r'^version = "[^"]+"', f'version = "{new}"', text, flags=re.M)
PYPROJECT.write_text(text)

print(f"bumped {current} -> {new}", file=sys.stderr)
print(new)
