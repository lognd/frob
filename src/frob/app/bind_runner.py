from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from frob.bind import check, scan_bindings, scan_sources


# frob:doc docs/app.md#runners
def run(argv=None):
    p = argparse.ArgumentParser(
        prog="frob bind",
        description="Verify that binding declarations match source signatures",
    )
    p.add_argument("path", help="Project root to scan")
    p.add_argument("--json", action="store_true", help="Output JSON")
    p.add_argument(
        "--list-bindings", action="store_true", help="List all BIND declarations"
    )
    p.add_argument(
        "--list-sources",
        action="store_true",
        help="List all detected source signatures",
    )
    args = p.parse_args(argv)

    root = Path(args.path)
    if not root.exists():
        print(f"error: {root} does not exist", file=sys.stderr)
        sys.exit(1)

    if args.list_bindings:
        items = scan_bindings(root)
        if args.json:
            print(json.dumps([vars(i) for i in items], indent=2))
        else:
            for b in items:
                print(f"{b.file}:{b.line}  {b.signature}  [{b.kind}]")
        return

    if args.list_sources:
        items = scan_sources(root)
        if args.json:
            print(json.dumps([vars(i) for i in items], indent=2))
        else:
            for s in items:
                print(f"{s.file}:{s.line}  {s.signature}  [{s.kind}]")
        return

    mismatches = check(root)
    if args.json:
        out = {
            "root": str(root),
            "ok": len(mismatches) == 0,
            "mismatches": [
                {
                    "file": m.binding.file,
                    "line": m.binding.line,
                    "signature": m.binding.signature,
                    "issue": m.issue,
                }
                for m in mismatches
            ],
        }
        print(json.dumps(out, indent=2))
    else:
        if not mismatches:
            print("ok: all bindings match source declarations")
        else:
            for m in mismatches:
                print(f"{m.binding.file}:{m.binding.line}: {m.issue}")
            sys.exit(1)
