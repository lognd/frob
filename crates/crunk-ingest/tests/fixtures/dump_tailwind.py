"""Dump the Python crunk Tailwind theme of a project as the flat golden JSON the Rust tests pin.

Usage (the Python crunk checkout is read-only, only imported):

    <crunk>/.venv/bin/python dump_tailwind.py <project-root> --out <name>.theme.json

Writes `{"<namespace>.<key>": "<value>"}`, sorted by key, with `var()` references resolved,
in the shape of `TailwindTheme::theme_map` in crunk-ingest.
"""

import json
import sys
from pathlib import Path

from crunk.ingest import ingest_tree
from crunk.spec import load_spec


def main(argv):
    root = Path(argv[1])
    out = Path(argv[argv.index("--out") + 1])
    styles = ingest_tree(load_spec(root))
    theme = styles.tailwind
    flat = {}
    for entry in theme.entries if theme else []:
        name = f"{entry.namespace}.{entry.key}" if entry.namespace else entry.key
        flat[name] = entry.resolved if entry.resolved is not None else entry.value
    out.write_text(json.dumps(dict(sorted(flat.items())), indent=2) + "\n", encoding="ascii")


if __name__ == "__main__":
    main(sys.argv)
