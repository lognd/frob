"""Dump the CSS part of the Python crunk ProjectStyles of a project as JSON.

Usage (the Python crunk checkout is read-only, only imported):

    <crunk>/.venv/bin/python dump_ingest.py <project-root> --out <name>.styles.json

Writes one JSON document to the path after `--out`: the CSS-only `ProjectStyles` with paths
relative to the project root and spans as code-point offsets.
JSX sheets and the Tailwind theme are left out (other tickets).
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
        "waivers": [{"rule": w.rule, "reason": w.reason, "line": w.line} for w in d.waivers],
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
                "bucket": s.bucket.value if s.bucket else None,
                "component": s.component,
                "declarations": [dump_decl(d) for d in s.declarations],
                "class_selectors": [{"name": c.name, "line": c.line} for c in s.class_selectors],
                "custom_props": [{"name": c.name, "line": c.line} for c in s.custom_props],
                "orphan_waivers": [
                    {"rule": w.rule, "reason": w.reason, "line": w.line} for w in s.orphan_waivers
                ],
                "media_queries": [
                    {"prelude": m.prelude, "min_px": m.min_px, "max_px": m.max_px, "line": m.line}
                    for m in s.media_queries
                ],
            }
            for s in styles.sheets
            if s.bucket is None or s.bucket.value != "jsx"
        ],
        "strays": [rel(p, root) for p in styles.strays],
        "diagnostics": [
            {"path": rel(d.path, root), "message": d.message}
            for d in styles.diagnostics
            if not d.path.suffix in (".tsx", ".ts", ".jsx")
        ],
        "ungoverned": [rel(p, root) for p in styles.ungoverned],
    }
    target = Path(sys.argv[sys.argv.index("--out") + 1])
    target.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")


main()
