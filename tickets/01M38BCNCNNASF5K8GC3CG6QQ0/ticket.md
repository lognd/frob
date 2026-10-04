+++
id = "01M38BCNCNNASF5K8GC3CG6QQ0"
title = "TODO001/gitio working_diff: merge-base against local main fails under shallow checkout (no local main ref)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-09-24T00:00:02Z"
aliases = ["T-5525"]
labels = ["milestone:v0.534.0"]
scope = ["src/frob/gitio.py"]
+++

Found draining CI run 35951365410 (windows-latest self-gate, dev 9e0c89bb19).
Not Windows-specific (verified: default shallow `actions/checkout@...v7.0.1`
never fetches a local `main` ref on either runner OS -- this is a real
detector defect, not debt).

win-selfgate.txt:1030-1032:
  WARNING: gitio: git merge-base HEAD main failed (rc=128): fatal: Not a
  valid object name main
  WARNING: gitio: working_diff: no merge-base for base='main'
  WARNING: run_gates: working_diff failed (GitFailed: git subprocess
  failed); diff-dependent gates see no touched set
  [gate:TODO] TODO001: working diff against base='main' failed to load
  (bad --base, detached HEAD, or a git failure); TODO001 cannot be
  evaluated -- this is a load failure, not a clean/empty diff, so it is
  not silently passing

Fix: the working-diff resolver that computes `git merge-base HEAD main`
(src/frob/gitio, exact symbol TBD -- grep for the "no merge-base for
base=" message) should fall back to `origin/main` (or the actually-fetched
base ref/remote-tracking branch) when the local `main` ref does not exist,
instead of hard-failing TODO001 (and any other diff-dependent gate) with a
load failure. Add a test that simulates a checkout with no local `main`
ref (only `origin/main` fetched, as a shallow CI checkout produces) and
asserts the working diff still resolves.

frob:tests tests covering the working-diff resolver's base-ref fallback (add one)
