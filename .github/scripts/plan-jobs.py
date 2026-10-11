#!/usr/bin/env python3
"""Map changed paths (one per line on stdin) to the CI job sets that must run.

Prints `key=value` lines for $GITHUB_OUTPUT: rust, full, crunk, node.

- rust: some file outside the prose set changed (any Rust job can be affected).
- crunk: a crunk crate or docs/crunk changed.
- full: a change outside crunk (a gob-* crate, frob, grimble, a root file, a workflow ...)
  needs the whole workspace; a gob-* change runs all three products (monorepo.md 4).
- node: the node Tailwind runtime changed; it feeds only the optional node job.

A crunk-only change sets rust=true, crunk=true, full=false: the workspace `rust` job is
skipped and the `crunk` job runs instead.
"""
# frob:ticket 01M43ARWT173GKANZ322H41VF1
import re
import sys

# Paths no Rust job reads. docs/guides, docs/crunk, docs/reference and docs/schemas are read by
# tests or by the generated-file check, so they are NOT here.
PROSE = re.compile(r"^(tickets/|changelog\.d/|notes/|docs/(design|decisions|migration)/)")
CRUNK = re.compile(r"^(crates/crunk(-[^/]+)?/|docs/crunk/)")
NODE = re.compile(r"^crates/crunk-tailwind/(node|tests)/")


def plan(paths):
    """Return the job-set flags for the changed `paths` as a dict of str to bool."""
    rest = [p for p in paths if p and not PROSE.match(p)]
    return {
        "rust": bool(rest),
        "full": any(not CRUNK.match(p) for p in rest),
        "crunk": any(CRUNK.match(p) for p in rest),
        "node": any(NODE.match(p) for p in rest),
    }


if __name__ == "__main__":
    flags = plan([line.strip() for line in sys.stdin])
    for key, value in flags.items():
        print(f"{key}={'true' if value else 'false'}")
