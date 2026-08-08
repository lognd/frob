"""Verify that claimed land commits are genuinely ancestors of main.

WHY THIS EXISTS. An agent's Done report is not evidence. Several land
reports in this repo have claimed `verified=True` while the work was NOT on
main -- in one case a ticket read `done` with its entire deliverable absent,
four separate times. The only trustworthy check is
`git merge-base --is-ancestor <sha> <ref>`, and running it by hand invites
the other failure this guards against: a mistyped short sha reports MISSING
for work that actually landed, which happened twice.

Pass full shas when you have them; this script reports a bad/unknown sha as
UNKNOWN-SHA rather than MISSING, so a typo is never mistaken for lost work.

Usage:
    python3 scripts/verify_lands.py <sha> [<sha> ...] [--ref main]
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _git(args: list[str]) -> subprocess.CompletedProcess:
    """Run git in the repo root, never raising on non-zero exit."""
    return subprocess.run(
        ["git", "-C", str(REPO), *args],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def resolve(sha: str) -> str | None:
    """Full commit id for `sha`, or None when git cannot resolve it."""
    done = _git(["rev-parse", "--verify", f"{sha}^{{commit}}"])
    return done.stdout.strip() if done.returncode == 0 else None


def is_ancestor(sha: str, ref: str) -> bool:
    """True when `sha` is an ancestor of `ref` (i.e. it really landed)."""
    return _git(["merge-base", "--is-ancestor", sha, ref]).returncode == 0


def subject(sha: str) -> str:
    """One-line subject for `sha`, for eyeballing that it is the right commit."""
    return _git(["log", "-1", "--format=%s", sha]).stdout.strip()


def main() -> int:
    """Check every sha against `ref`; exit 1 if any is missing or unknown."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("shas", nargs="+")
    parser.add_argument("--ref", default="HEAD")
    args = parser.parse_args()

    bad = 0
    for sha in args.shas:
        full = resolve(sha)
        if full is None:
            print(f"UNKNOWN-SHA {sha}  (typo? not a commit in this repo)")
            bad += 1
        elif is_ancestor(full, args.ref):
            print(f"ON {args.ref:9} {full[:12]}  {subject(full)[:80]}")
        else:
            print(f"MISSING    {full[:12]}  NOT an ancestor of {args.ref}")
            bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
