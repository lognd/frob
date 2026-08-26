---
id: T-2980
title: 'ubuntu-latest CI hangs in the Test step for 2+ hours: no green baseline exists
  on any platform'
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: critical
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
First CI run of main after the push (run 32968539246, job 98176563537,
ubuntu-latest) sat on the `Test` step for over two hours without completing.
Every step before it passed: checkout, uv, Rust, cargo cache, sync deps, native
extension build, `cargo test` for BOTH frob-core and strata-core, Lint, and
Typecheck. The pytest step itself hangs.

This is the most important open defect in the repo right now:

- There is NO green baseline on ANY platform. Windows fails at Typecheck, macOS
  has a large uncharacterized failure set (T-2971), and our PRIMARY development
  platform never finishes at all.
- It is a HANG, not a failure. A failure gives a traceback; a hang gives
  nothing, and it silently consumes the CI budget for every run.
- It explains an earlier mystery: a previous triage (T-2943) found the ubuntu
  job cancelled mid-run, which is why a Linux-reproducible fixture bug looked
  macOS-specific for an entire investigation. A hung ubuntu job has been hiding
  real failures behind it.

INVESTIGATION LEADS -- these are candidates, not conclusions. Measure before
believing any of them:

- Several things touched today plausibly wait forever rather than fail:
  `_coverage_wait.py` (fcntl guarding changed under T-2952), `_socketd.py`
  (socket path relocated under T-2945, daemon class guarded under T-2961), the
  land/ledger/baseline flock paths (`_lock.py`, `_land.py`, `_store.py`, with
  msvcrt/fcntl backends added under T-2934/T-2918), and the forkserver reaping
  path (`_reap.py`, T-2880/T-2936).
- A lock acquired with no timeout, a socket accept with no deadline, or a
  subprocess read that never sees EOF all present exactly like this.
- `PYTHONFAULTHANDLER=1 timeout -s ABRT <n> <cmd>` dumps a stuck process stack
  in one command and has localized a hotspot in this repo before. Prefer it
  over reasoning about which candidate is guilty.
- pytest `--timeout`, `-x --durations`, and `faulthandler_timeout` can localize
  which test node wedges.

ACCEPTANCE

- Given the full test suite on Linux, when it runs, then it TERMINATES -- pass
  or fail, but it completes and reports.
- The specific hanging test node or nodes are identified by name, and the
  mechanism is stated: which lock, socket, or read waits forever, and why.
- A hang cannot silently return. Whatever waits must acquire a bounded timeout
  and fail LOUDLY on expiry rather than blocking indefinitely. A bare timeout
  added with no loud failure path is not a fix.
- Must-still-pass: the real failures in the suite are still reported as
  failures. Do not make the suite terminate by skipping the tests that wedge --
  that converts a hang into an invisible gap.
