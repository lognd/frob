---
id: T-2763
title: Coverage data is 14 days stale because the refresh OOMs in parallel and overruns
  serially, leaving TEST005 silently unmeasurable
state: queued
kind: bug
origin: human
created: '2026-08-20'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
## TEST005/TEST006 have been silently unmeasurable for 14 days

`.frob/coverage.partial.xml` is dated **Aug 6**. The committed
`frob-coverage.lock.json` is Aug 19. There is no `coverage.xml` anywhere
in the repo or in any worktree. Today is Aug 20, and hundreds of tickets
have landed in that window.

TWO INDEPENDENT AGENTS hit this today and both correctly refused to
report a number:
- one ran an unscoped `frob check --only test --no-cache` and got 54
  `gate:TEST` diagnostics of which **ZERO** were TEST005 -- the present
  ones were TEST014(32)/TEST003(20)/TEST001(1)/TEST006(1), all rules that
  do not need coverage data
- the other confirmed the same and cited playbook 6c: TEST005 SILENTLY
  SKIPS any file with no coverage data, so an absent `coverage.xml` reads
  as "nothing to flag", not "clean"

That is the silent-zero shape exactly: the gate reports nothing because
it cannot see, and nothing distinguishes that from a clean tree.

## The refresh cannot complete

`make coverage` is `frob ticket reconcile --apply && frob doctor &&
frob coverage --full`, and the playbook (3c/6b) makes it coordinator-only,
so no dispatched agent can run it. I ran it myself. Measured:

    coverage_refresh: explicit --full -- running the full suite
    ERROR: pytest --cov=src/frob --cov-report= -n 12 exited 3 and matched
    the xdist worker-crash signature (T-1672: a worker process was killed,
    most often OOM) -- retrying ONCE serially (-p no:xdist)
    coverage_refresh: neutralizing xdist token(s) ... for the serial retry

The parallel run OOMs at `-n 12`. The serial fallback then exceeds a
580s budget and was killed (exit 124). No `coverage.xml` was produced;
the root was left clean, so there is no residue -- but there is also no
measurement.

So the only path to refreshing coverage is one that OOMs in parallel and
overruns serially. That is why the data is 14 days old: not neglect, an
unrunnable step.

## Why this matters beyond one stale file

TEST005 is a RATCHET. T-1953 (held by owner decision) exists to raise its
floors. A ratchet whose input is 14 days stale cannot be raised safely,
and a ratchet that silently passes on absent data is not a ratchet at
all -- it is a gate that reports success when it has nothing to check.

## What to determine

1. Why does `-n 12` OOM? The T-1672 signature is already recognised in
   code, so the crash is expected -- but the worker count appears not to
   adapt. Consider deriving it from available memory rather than CPU
   count, the same way T-2715 made the sweep budget derive from measured
   stage timings instead of a frozen constant.
2. What does a serial full-coverage run actually cost? Measure it before
   choosing a strategy; nobody currently knows.
3. Should TEST005 REFUSE rather than skip when coverage data is absent or
   older than some threshold? A loud "cannot measure" is worth more than
   a silent pass, and this repo has spent the day fixing exactly that
   class of defect (T-2713, T-2715, T-2744).

## Positive controls, both directions

- with fresh coverage present, TEST005 fires on a genuinely uncovered
  file and does not fire on a covered one
- with coverage ABSENT or stale beyond threshold, the gate reports
  UNMEASURED/refuses -- it must not report zero findings
- the refresh completes on this machine without OOM, and its cost is
  stated

## Note

Do not "fix" this by lowering the coverage bar or by making the refresh
sample fewer tests. The measurement being expensive is not the bug; the
bug is that failing to measure is indistinguishable from measuring clean.
