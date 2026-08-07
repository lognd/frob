---
id: T-1436
title: Warm daemon forkserver pool competes with foreground frob check for CPU
state: done
kind: bug
origin: agent
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/serve/_tools.py
- src/frob/gates/__init__.py
- docs/modules/gates.md
- docs/modules/serve.md
- tests/test_serve.py
- docs/guides/agent-playbook.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'T-1436''s own body says the fix belongs in frob.serve._tools''s

    parallel-execution paths, but the actual forkserver pool sizing knob

    (_open_process_pool''s proc_workers = min(len(jobs), cpu_count())) lives in

    src/frob/gates/__init__.py, which run_gates()/frob_check_delta call into.

    There is no existing env var or run_gates() parameter that lets a caller

    (the daemon) request a smaller/lazier pool without editing

    _open_process_pool itself. Widening scope to add a narrow,

    backward-compatible optional knob there (not touching any other gate

    logic) is the minimal change that makes T-1436''s fix land in the file it

    actually names as the mechanism.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: docs/modules/gates.md
  reason: the pool-cap change's doc and test obligations live here; adds were refused
    mid-work by T-1420's since-released standing lease
  actor: logan
  at: '2026-08-02'
- op: add
  glob: docs/modules/serve.md
  reason: the pool-cap change's doc and test obligations live here; adds were refused
    mid-work by T-1420's since-released standing lease
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/test_serve.py
  reason: the pool-cap change's doc and test obligations live here; adds were refused
    mid-work by T-1420's since-released standing lease
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/gates/__init__.py
  reason: the pool-cap change's doc and test obligations live here; adds were refused
    mid-work by T-1420's since-released standing lease
  actor: logan
  at: '2026-08-02'
- op: add
  glob: docs/guides/agent-playbook.md
  reason: FROB_NO_GATE_CACHE stale-reading guidance belongs in the playbook per the
    coordinator's dispatch note
  actor: logan
  at: '2026-08-02'
evidence:
- tests/test_serve.py::TestRunTouchedTests::test_no_diff_selects_nothing
- tests/test_gates.py::TestProcessPoolGates::test_combined_parallel_path_matches_fully_serial_path
designated_repro_test: null
threat: null
component: null
---
T-1378 fixed the socketd-level defects (frob_shutdown now actually exits
the process, and every multiprocessing.active_children() is reaped
before Python's own atexit hook would otherwise hang for 20+ seconds).

The third defect T-1378 measured is still open: with a warm daemon up,
`frob check --only gates --delta --json` measured SLOWER than the same
command with FROB_NO_DAEMON=1, and system load average went from ~0.4
idle to 5-8 while a single check ran. The root cause is a persistent
multiprocessing forkserver pool that frob.serve._tools's
parallel-execution paths (frob_check_delta / frob_run_touched_tests)
keep warm across requests inside the daemon process, competing with the
foreground check for the same cores on a small (4-core) machine -- this
lives entirely in frob.serve._tools, not src/frob/serve/_socketd.py
(T-1378's declared scope), so it could not be fixed there.

T-1379 already made the daemon opt-in (FROB_DAEMON, not
default-enabled), which removes this as a default-install risk, but a
user who opts in still pays the regression measured here. Investigate
whether the pool should be sized down, made lazy (spawned only on the
first parallel-execution request, not eagerly), or shared/reused
differently, and re-measure `frob check --only gates --delta --json`
warm-daemon vs FROB_NO_DAEMON=1 to confirm parity or a real win.