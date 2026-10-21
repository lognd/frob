#!/usr/bin/env python3
"""Map changed paths (one per line on stdin) to the CI job sets that must run.

The mapping is data: crates/gob-dev/changes.toml (the same file `cargo dev changes` embeds, so
this script and the Rust tool cannot disagree; crates/gob-dev/tests/ci_plan.rs checks they agree).
Prints `key=value` lines for $GITHUB_OUTPUT: rust, full, crunk, node, workflows, docs_only.

- rust: some file outside the docs class changed (any Rust job can be affected).
- crunk: a crunk crate or docs/crunk changed.
- full: a change outside crunk (a gob-* crate, frob, grimble, a root file, a workflow ...)
  needs the whole workspace; a gob-* change runs all three products (monorepo.md 4).
- node: the node Tailwind runtime changed; it feeds only the optional node job.
- workflows: a workflow or local action changed.
- docs_only: every changed path is documentation no Rust job reads (fmt, gen and check only).

A crunk-only change sets rust=true, crunk=true, full=false: the workspace `rust` job is
skipped and the `crunk` job runs instead.
"""
# frob:ticket 01M43ARWT173GKANZ322H41VF1
# frob:ticket 01M47QVD03PGCAZ301WHC5Q4MF
import pathlib
import sys
import tomllib

MAP = pathlib.Path(__file__).resolve().parents[2] / "crates" / "gob-dev" / "changes.toml"


def load(path=MAP):
    """Return the class name to path-prefix tuple mapping from changes.toml."""
    classes = {}
    for entry in tomllib.loads(path.read_text(encoding="utf-8"))["class"]:
        classes.setdefault(entry["name"], []).extend(entry["prefixes"])
    return {name: tuple(prefixes) for name, prefixes in classes.items()}


def plan(paths, classes=None):
    """Return the job-set flags for the changed `paths` as a dict of str to bool."""
    classes = classes or load()
    paths = [p for p in paths if p]
    rest = [p for p in paths if not p.startswith(classes["docs"])]
    return {
        "rust": bool(rest),
        "full": any(not p.startswith(classes["crunk"]) for p in rest),
        "crunk": any(p.startswith(classes["crunk"]) for p in rest),
        "node": any(p.startswith(classes["node"]) for p in rest),
        "workflows": any(p.startswith(classes["workflows"]) for p in rest),
        "docs_only": bool(paths) and not rest,
    }


if __name__ == "__main__":
    flags = plan([line.strip() for line in sys.stdin])
    for key, value in flags.items():
        print(f"{key}={'true' if value else 'false'}")
