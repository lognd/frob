---
id: T-2934
title: 'Fix 5 real PLATFORM001 findings: fcntl warn-and-continue in _lock.py/_land.py/_land_git_ops.py/_store.py'
state: in-progress
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
- src/frob/process/_lock.py
- src/frob/tickets/_land.py
- src/frob/tickets/_land_git_ops.py
- src/frob/tickets/_store.py
- src/frob/gates/_walk_lint.py
- tests/test_walk_lint_gate.py
- docs/modules/process.md
- docs/modules/gates.md
- docs/modules/tickets-landing.md
- tests/unit/test_process_lock.py
- tests/test_ticket_land.py
- tests/unit/test_ticket_store.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_walk_lint.py
  reason: 'narrow PLATFORM001 false positive: return Ok()/Err() (typani) is a declared
    refusal, not silent warn-and-continue'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_walk_lint_gate.py
  reason: 'narrow PLATFORM001 false positive: return Ok()/Err() (typani) is a declared
    refusal, not silent warn-and-continue'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/process.md
  reason: doc anchors for touched public symbols
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/gates.md
  reason: doc anchors for touched public symbols
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: doc anchors for touched public symbols
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/test_process_lock.py
  reason: msvcrt backend + loud refusal tests for derived_state_lock
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_ticket_land.py
  reason: msvcrt backend + loud refusal tests for _land_lock
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: ledger_lock msvcrt backend + loud refusal tests
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2919's new PLATFORM001 gate (frob.gates._walk_lint) fired 5 real,
pre-existing warn-and-continue findings on this repo's own source the
first time it ran (measured, not hypothetical):

  src/frob/process/_lock.py:265
  src/frob/tickets/_land.py:649
  src/frob/tickets/_land_git_ops.py:410
  src/frob/tickets/_store.py:257
  src/frob/tickets/_store.py:357

Each is the same shape T-2918 fixed in _rapid_sweep.py::_baseline_lock:
an `fcntl`-absence guard (or `_land_git_ops.py`'s `_fcntl`) that logs a
warning and proceeds as if the missing lock did not matter, rather than
declaring a real cross-platform backend or refusing loudly. Per the
MEASURED EVIDENCE in the T-2917/T-2918/T-2919 series' own dispatch
brief, only three files in this repo carry ANY sys.platform/os.name
guard at all -- these 5 sites are very likely part of the same larger
population that brief's own grep undercounted.

Triage each site individually (some may warrant the same msvcrt-backend
treatment T-2918 gave `_rapid_sweep.py`, others may only need the loud-
refusal half if a genuine Windows backend does not make sense for that
lock's specific correctness contract -- e.g. `_land.py`'s land lock is
a much longer-held, higher-stakes lock than the baseline lock, so a
timeout-degrade posture may not be appropriate there at all and a loud
refusal may be the ONLY correct choice). Out of scope for T-2919, which
built the DETECTOR; this ticket is the fix-the-5-real-findings-it-found
follow-up.
