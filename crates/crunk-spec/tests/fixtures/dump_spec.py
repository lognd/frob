"""Dump the Python crunk spec of every valid fixture as the reference JSON.

Usage (the Python crunk checkout is read-only, only imported):

    <crunk>/.venv/bin/python dump_spec.py valid/*.toml

Writes `<name>.spec.json` next to each `<name>.toml`: `DesignSpec.model_dump(mode="json")`
without `root`, and `<name>.order.json`: the declaration order of every user-keyed map. The
Rust parity test compares the Rust `DesignSpec` against these files.
"""

import json
import sys
import tempfile
from pathlib import Path

from crunk.spec import load_spec

for arg in sys.argv[1:]:
    src = Path(arg)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "crunk.toml").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        result = load_spec(root)
        if result.is_err:
            sys.exit(f"{src}: {result.danger_err}")
        dump = result.danger_ok.model_dump(mode="json")
        dump.pop("root")
        out = src.with_suffix(".spec.json")
        out.write_text(json.dumps(dump, indent=2) + "\n", encoding="utf-8")
        order = {
            "palette": list(dump["palette"]),
            "roles": list(dump["roles"]),
            "layers": list(dump["layers"]),
            "stacks": list(dump["typography"]["stacks"]),
            "lint_rules": list(dump["lint"]["rules"]),
            "breakpoints": list(dump["breakpoints"]["points"]),
            "platforms": list(dump["platforms"]),
            "screens": list(dump["screens"]),
            "sessions": list(dump["sessions"]),
            "mock_sets": list(dump["mock_sets"]),
        }
        order_out = src.with_suffix(".order.json")
        order_out.write_text(json.dumps(order, indent=2) + "\n", encoding="utf-8")
        print("wrote", out, order_out)
