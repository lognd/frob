from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from frob.bind import check, scan_bindings, scan_sources


def _build_bind_parser() -> argparse.ArgumentParser:
    """Argument parser for `frob bind`."""
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
    return p


def _print_items(items, as_json: bool) -> None:
    """Print scanned binding/source items as JSON or one line each."""
    if as_json:
        print(json.dumps([vars(i) for i in items], indent=2))
        return
    for i in items:
        print(f"{i.file}:{i.line}  {i.signature}  [{i.kind}]")


def _report_mismatches(mismatches, as_json: bool, root: Path) -> None:
    """Print binding/source mismatches; exit non-zero on any text-mode mismatch."""
    if as_json:
        out = {
            "root": str(root),
            "ok": not mismatches,
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
        return
    if not mismatches:
        print("ok: all bindings match source declarations")
        return
    for m in mismatches:
        print(f"{m.binding.file}:{m.binding.line}: {m.issue}")
    sys.exit(1)


# frob:doc docs/modules/app.md#runners
def run(argv=None):
    args = _build_bind_parser().parse_args(argv)

    root = Path(args.path)
    if not root.exists():
        print(f"error: {root} does not exist", file=sys.stderr)
        sys.exit(1)

    if args.list_bindings:
        _print_items(scan_bindings(root), args.json)
        return
    if args.list_sources:
        _print_items(scan_sources(root), args.json)
        return
    _report_mismatches(check(root), args.json, root)
