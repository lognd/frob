#!/usr/bin/env python3
"""Check the committed corpus: index completeness, ASCII-only, no home paths.

Usage: python verify.py index|text
Exits non-zero (with the offending items on stderr) on any violation.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
log = logging.getLogger("crunk_parity.verify")
LEAK = re.compile(r"/home/|/tmp/|/Users/|claude-1000|pytest-of-")


def check_index() -> list[str]:
    """Every E2E-01..58 and INT-01..12 must name existing fixture/expected paths."""
    idx = json.loads((HERE / "index.json").read_text())["e2e_int"]
    errs = []
    want = [f"E2E-{n:02d}" for n in range(1, 59)] + [f"INT-{n:02d}" for n in range(1, 13)]
    for ident in want:
        e = idx.get(ident)
        if e is None:
            errs.append(f"{ident}: missing from index")
            continue
        paths = e["fixture_dirs"] + e["expected_dirs"]
        if "fixture" in e:
            paths.append(e["fixture"])
        if "golden" in e:
            paths.append(e["golden"])
        if not paths and not e.get("source"):
            errs.append(f"{ident}: names no fixture, expected files or source")
        errs += [f"{ident}: missing {p}" for p in paths if not (HERE / p).exists()]
    return errs


def check_text() -> list[str]:
    """No corpus file may contain a home/tmp path or a non-ASCII byte."""
    errs = []
    for p in sorted(HERE.rglob("*")):
        if not p.is_file() or "__pycache__" in p.parts or p.name in ("verify.py", "regen.py"):
            continue
        data = p.read_bytes()
        if not data.isascii():
            errs.append(f"non-ASCII: {p.relative_to(HERE)}")
        elif LEAK.search(data.decode("ascii")):
            errs.append(f"path leak: {p.relative_to(HERE)}")
    return errs


def main() -> int:
    """Run the requested check."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    which = sys.argv[1] if len(sys.argv) > 1 else ""
    checks = {"index": check_index, "text": check_text}
    if which not in checks:
        print(__doc__, file=sys.stderr)
        return 2
    errs = checks[which]()
    for e in errs:
        log.error(e)
    log.info("%s: %d problem(s)", which, len(errs))
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
