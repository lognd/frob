#!/usr/bin/env python3
"""Compare the land cone verdict with the full check on recent lands (build-test-ci.md fast lands).

For each of the newest N land commits (`tickets(land): ~HANDLE ...`, oldest first) the script
checks the land commit out in a throwaway worktree and runs two checks there:

- scoped: `frob check --ticket HANDLE --base PREV`, the cone a land evaluates, where PREV is the
  previous land commit (the window of changes since the last land);
- full: `frob check` over the whole repository, and the same full check at PREV.

A finding the land introduced is one in the full check at the land commit and not at PREV
(matched by fingerprint). The cone DISAGREES when it misses such a finding: the finding is new,
the full check fails on it, and the scoped check does not report it. Each disagreement is a defect
of the cone; the script prints them and exits 1. A ticket the scoped check cannot resolve is
skipped with a note, never counted as agreement.
"""
# frob:ticket 01M51CKH84ZBS7G3SP7XM0FM1F
import json
import logging
import re
import subprocess
import sys
import tempfile

log = logging.getLogger("cone-compare")
LAND = re.compile(r"^tickets\(land\): (~[0-9A-Z]+)\b")
SEVERITY = {"error": 3, "warn": 2, "warning": 2, "advisory": 1}


def new_findings(full_at_land, full_at_prev, fail_on="error"):
    """Fingerprints of failing findings in `full_at_land` that `full_at_prev` lacks."""
    floor = SEVERITY.get(fail_on, 3)
    old = {f["fingerprint"] for f in full_at_prev}
    return {
        f["fingerprint"]: f
        for f in full_at_land
        if SEVERITY.get(f.get("severity"), 0) >= floor and f["fingerprint"] not in old
    }


def missed(full_at_land, full_at_prev, scoped, fail_on="error"):
    """Findings the land introduced that the scoped (cone) check did not report."""
    seen = {f["fingerprint"] for f in scoped}
    return [f for fp, f in new_findings(full_at_land, full_at_prev, fail_on).items() if fp not in seen]


def sh(*args, cwd=None):
    """Run a command and return its stdout; the exit status is not an error."""
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False).stdout


def findings(frob, cwd, *extra):
    """Findings of `frob check` run in `cwd`, or None when the output is not an envelope."""
    out = sh(frob, "check", "--json", "--fail-on", "none", *extra, cwd=cwd)
    for line in reversed(out.splitlines()):
        if line.startswith("{") and '"verb"' in line:
            data = json.loads(line).get("data") or {}
            return data.get("findings", [])
    return None


def lands(count):
    """The newest `count` (sha, handle) land commits on first-parent history, oldest first."""
    log_out = sh("git", "log", "--first-parent", "--format=%H %s", "-n", "400")
    found = []
    for row in log_out.splitlines():
        sha, _, subject = row.partition(" ")
        m = LAND.match(subject)
        if m and m.group(1) not in {h for _, h in found}:
            found.append((sha, m.group(1)))
    return list(reversed(found[: count + 1]))


def main(argv):
    """Compare the cone with the full check on the newest lands; return the exit status."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    frob, count = argv[1], int(argv[2]) if len(argv) > 2 else 3
    window = lands(count)
    bad = 0
    for (prev, _), (sha, handle) in zip(window, window[1:]):
        with tempfile.TemporaryDirectory() as tmp:
            sh("git", "worktree", "add", "--detach", tmp, sha)
            try:
                scoped = findings(frob, tmp, "--ticket", handle, "--base", prev)
                full = findings(frob, tmp)
                sh("git", "checkout", "--detach", prev, cwd=tmp)
                before = findings(frob, tmp)
            finally:
                sh("git", "worktree", "remove", "--force", tmp)
        if scoped is None or full is None or before is None:
            log.warning("%s at %s: a check produced no envelope; skipped", handle, sha[:9])
            continue
        gaps = missed(full, before, scoped)
        for f in gaps:
            log.error("cone defect %s at %s: %s %s:%s %s", handle, sha[:9], f["rule"], f["file"], f["line"], f["message"])
        log.info("%s at %s: %d new findings missed by the cone", handle, sha[:9], len(gaps))
        bad += len(gaps)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
