---
id: T-5525
title: 'TODO001/gitio working_diff: merge-base against local main fails under shallow
  checkout (no local main ref)'
state: queued
kind: bug
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/gitio.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
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
