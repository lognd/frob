"""Dump the JSX part of the Python crunk ProjectStyles of a project as JSON.

Usage (the Python crunk checkout is read-only, only imported):

    <crunk>/.venv/bin/python dump_jsx.py <project-root> --out <name>.jsx.json

Writes one JSON document: every `Bucket.JSX` sheet (paths relative to the project root, spans as
code-point offsets) with its style-prop declarations and className utility tokens, and the
diagnostics of the JSX files.
"""

import json
import sys
from pathlib import Path

from crunk.ingest import ingest_tree
from crunk.spec import load_spec


def rel(path, root):
    try:
        return Path(path).resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def dump_decl(d):
    return {
        "prop": d.prop,
        "value": d.value,
        "line": d.line,
        "span": list(d.span),
        "colors": [{"hex": c.color.to_hex(), "span": list(c.span)} for c in d.colors],
        "lengths": [
            {"raw": l.length.raw, "px": l.length.px, "kind": l.length.kind.value, "span": list(l.span)}
            for l in d.lengths
        ],
        "var_refs": [{"name": v.name, "span": list(v.span)} for v in d.var_refs],
    }


def main():
    root = Path(sys.argv[1]).resolve()
    spec_r = load_spec(root)
    if spec_r.is_err:
        sys.exit(f"spec: {spec_r.danger_err}")
    spec = spec_r.danger_ok
    res = ingest_tree(root, spec)
    if res.is_err:
        sys.exit(f"ingest: {res.danger_err}")
    styles = res.danger_ok
    out = {
        "sheets": [
            {
                "path": rel(s.path, root),
                "component": s.component,
                "declarations": [dump_decl(d) for d in s.declarations],
                "utilities": [
                    {"name": u.name, "line": u.line, "variants": list(u.variants)}
                    for u in s.utilities
                ],
            }
            for s in styles.sheets
            if s.bucket is not None and s.bucket.value == "jsx"
        ],
        "diagnostics": [
            {"path": rel(d.path, root), "message": d.message}
            for d in styles.diagnostics
            if d.path.suffix in (".tsx", ".ts", ".jsx")
        ],
    }
    target = Path(sys.argv[sys.argv.index("--out") + 1])
    target.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")


main()
