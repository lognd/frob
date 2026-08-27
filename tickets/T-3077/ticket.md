---
id: T-3077
title: CI still shells to make coverage instead of frob coverage --full
state: queued
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured for T-1382 (epic: decouple frob from the Makefile) using the
coordinator's own new CI evidence: run 33035660969 (2026-08-27) got
windows-latest through Lint (uv run ruff check) and Typecheck (uv run ty
check) for the first time, and reached the Test step (uv run pytest -q).
Test failed on all three platforms (ubuntu/windows/macos) with the same
shape of pre-existing failures plus an xdist worker timeout -- that
failure is NOT Makefile-related and is out of this ticket's scope.

The material gap for THIS epic: .github/workflows/ci.yml's own "coverage
stamp + delta baseline must be freshly measurable and clean (T-1366)"
step literally runs `make coverage` (not `uv run frob coverage --full`)
as its first line. Because the earlier Test step failed first, that line
was never reached on windows-latest in this run (shown as skipped/"-" in
`gh run view 33035660969`), so acceptance[1] ("GIVEN Windows... WHEN the
coverage workflow runs THEN it works without... GNU-make syntax") remains
UNVERIFIED in the one CI job that would actually prove or disprove it --
and if reached, it would depend on a `make` binary being present on
windows-latest, which is not installed by any preceding step in this
workflow.

Fix: change that CI step (and any other CI step still spelling `make
coverage`/`make <target>` instead of the frob subcommand it aliases) to
call `uv run frob coverage --full` directly, so the Windows job actually
exercises the make-free path this epic claims to have built, instead of
silently depending on `make` being available or never being reached.

Verification commands run:
gh run view 33035660969
  -> windows-latest: Lint OK, Typecheck OK, Test FAILED (pre-existing/xdist,
     unrelated), "coverage stamp..." step shown as skipped ("-")
grep -n "run: make coverage" .github/workflows/ci.yml
  -> present under the T-1366 "coverage stamp + delta baseline" step
