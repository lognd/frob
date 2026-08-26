---
id: T-2942
title: 'macOS CI: remaining small failure clusters needing individual triage (SYS107,
  FIFO pipe, timing threshold, resolved-root, load_lock)'
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/strata/test_sys003_calibration.py
- tests/unit/test_ticket_new_body_file_pipe_t2021.py
- tests/unit/perf/test_serial_pools.py
- tests/system/test_cli_ticket_land.py
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
Remaining small clusters from the 156-failure macOS run (T-2917 PR#1,
run 32920399634, job 98032723003) not covered by the other T-2930
follow-ups (AF_UNIX socket path, gitio returncode=128, PLATFORM001/
process-detection gaps), grouped because each is individually small
(1-6 failures) and none needed its own dedicated ticket on its own,
but all need real per-cluster triage rather than a blanket skip:

1. (4 failures) tests/unit/strata/test_sys003_calibration.py and
   test_selfconform.py -- SYS107/SYS003 findings on `_land.py:440` and
   `testsuite` binding 615 files. Already flagged in T-2930's own
   description as needing triage for "genuine pre-existing violation
   surfaced by a differently-ordered run" vs "environment artifact" --
   still unresolved, carrying forward verbatim.
2. (2 failures) tests/unit/test_ticket_new_body_file_pipe_t2021.py --
   `SystemExit: 1` reading a FIFO/pipe body-file on macOS; likely a
   real difference in named-pipe read semantics (blocking reopen,
   buffering) between Linux and macOS, needs a macOS-specific repro to
   confirm before assuming test-only.
3. (1 failure) tests/unit/perf/test_serial_pools.py -- hardcoded 0.05s
   timing threshold, measured 0.0808s on the macOS runner; almost
   certainly test-only fragility (a slower/differently-contended CI
   runner), fix is loosening the threshold or asserting a ratio instead
   of an absolute wall-clock bound -- verify it is not masking a real
   perf regression before loosening.
4. (6 failures) "resolved root /private/var/folders/..." assertions in
   tests/system/test_cli_evidence_enforcement.py, test_cli_ticket.py,
   test_cli_ticket_promote.py, test_cli_ticket_land.py -- likely
   downstream of the same gitio/git-repo-state issue tracked separately,
   but confirm independently since these assert on `ticket
   start/close/land`'s own root-resolution message specifically, not a
   raw git subprocess failure.
5. (2 failures) "load_lock: no lock file at /private/var/folders/..." --
   plausibly a real macOS path-realpath (`/var` symlink to `/private/
   var`) mismatch between where a lock file is written vs where it is
   looked up; distinct from cluster 4's "no repo" shape. Worth checking
   whether the writer and reader both call `.resolve()` consistently.
3 more single-count outliers (a JSON export golden mentioned in this
ticket's own description, a git-identity string comparison
`'Anka <runner...>' == 'frob-bot <...>'`, and 3 "Claude config DRIFT"
CI-environment-only failures unrelated to macOS specifically -- the
CI runner does not have `~/.claude` at all, a test-environment gap not
a portability defect) are noted here for completeness but are lowest
priority: CI-environment artifacts, not macOS-platform defects, and
should be triaged first for "does this fail on Linux CI too" before
assuming otherwise.
