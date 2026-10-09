"""Dump the Python crunk's static Tailwind theme of every fixture config.

Usage (the Python crunk checkout is read-only, only imported), from the fixtures directory:

    <crunk>/.venv/bin/python dump_tailwind.py

Writes `tailwind/goldens.json`: for each case, `parse_tailwind_config(static=True)` of the file with
the same `base_dir` / `config_path` the Rust test passes. The Rust test compares the theme maps.
"""

import json
from pathlib import Path

from crunk.ingest.tailwind import parse_tailwind_config

here = Path(__file__).parent / "tailwind"
cases = {
    "v4_fixture": ("v4/tailwind.css", False),
    "v3_literal": ("v3/literal.ts", True),
    "v3_cjs": ("v3/cjs.js", True),
    "v3_no_theme": ("v3/no_theme.ts", True),
    "bridge": ("bridge/entry.css", False),
    "hullbreach_config": ("hullbreach/web/tailwind.config.ts", True),
}
out = {}
for name, (rel, with_config_path) in cases.items():
    path = (here / rel).resolve()
    theme = parse_tailwind_config(
        path.read_text(encoding="utf-8"),
        base_dir=path.parent,
        config_path=path if with_config_path else None,
        static=True,
    )
    out[name] = theme
(here / "goldens.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("wrote", here / "goldens.json")
