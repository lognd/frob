"""Dump the Python crunk token list and Tailwind theme mapping of every spec fixture.

Usage (the Python crunk checkout is read-only, only imported):

    <crunk>/.venv/bin/python dump_tokens.py ../../../crunk-spec/tests/fixtures/valid/*.toml

Writes `<name>.tokens.json` next to this script: for each of the four combinations of
`[tailwind] namespace_keys` and `alpha_channels` (`ns<0|1>_a<0|1>`), the ordered
`entries(spec)` pairs and the flat `theme_mapping(spec)` the Python crunk computes. The Rust
parity test compares `TokenSet` against these files.
"""

import json
import sys
import tempfile
from pathlib import Path

from crunk.spec import load_spec
from crunk.tokens import entries, theme_mapping

here = Path(__file__).parent
for arg in sys.argv[1:]:
    src = Path(arg)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "crunk.toml").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        result = load_spec(root)
        if result.is_err:
            sys.exit(f"{src}: {result.danger_err}")
        base = result.danger_ok
        variants = {}
        for ns in (False, True):
            for alpha in (False, True):
                tw = base.tailwind.model_copy(
                    update={"namespace_keys": ns, "alpha_channels": alpha}
                )
                spec = base.model_copy(update={"tailwind": tw})
                variants[f"ns{int(ns)}_a{int(alpha)}"] = {
                    "entries": [list(pair) for pair in entries(spec)],
                    "theme": theme_mapping(spec),
                }
        out = here / f"{src.stem}.tokens.json"
        out.write_text(json.dumps(variants, indent=2) + "\n", encoding="utf-8")
        print("wrote", out)
