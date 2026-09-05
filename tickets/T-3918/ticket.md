---
id: T-3918
title: 'win32: split the real-defect (b) bucket of T-3914''s 49-failure classification
  into scoped leaves'
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_lock.py
- src/frob/gates/_profile_boundary.py
- src/frob/gates/_dup.py
- src/frob/check/_python.py
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
Filed under T-3505 (Windows portability epic), follow-up to T-3914's own
classification. T-3914 fixed bucket (a) (test-harness POSIX assumptions)
of the current 49-failure win32 set and deliberately left bucket (b)
(real product defects) unfixed to avoid scope creep -- see T-3914's own
body for the full per-test breakdown. This ticket is the tracking leaf
for splitting bucket (b) into scoped, individually-fixable tickets,
mirroring T-3661/T-3662/T-3664's pattern:

- Windows file-lock semantics (exclusive by default, unlike POSIX
  advisory locks): tests/ticket_land_suite/test_land_lock.py's
  PermissionError-reading-a-held-lock and a reclaim log line that never
  fires; tests/unit/test_graph_build_lock.py's cross-process build-lock
  test. A correctness-relevant PLATFORM001-class gap in the lock
  primitive itself.
- frob-cycle reporting zero diagnostics for a planted, unwaived cycle
  on win32 (tests/unit/test_cycle_waiver.py, 3 failures) -- a possible
  silent-zero measurement gap, needs investigation before CYCLE001 can
  be trusted on win32 at all.
- The pre-land lint-diff shifted-lines detector wrongly refusing on
  win32 (tests/test_ticket_land_lint_diff_attribution.py) -- plausibly
  CRLF-driven, would falsely block every Windows land if exercised for
  real.
- Further native-separator leaks in gate-internal path handling, same
  class as T-3662/T-3664/T-3914's own _new.py fix but different call
  sites: tests/unit/gates/test_profile_boundary.py (2),
  tests/unit/test_dup.py (1), tests/unit/arch_suite/test_misc.py's cpp
  symref test (1).
- Unconfirmed/lower-confidence items needing a second win32 data point
  before triage: tests/test_tickets_mutation_evidence.py (2),
  tests/ticket_land_suite/test_wip.py (1),
  tests/unit/test_land_release_out_of_tree.py (1),
  tests/unit/test_process_lock.py's BrokenProcessPool and git.exe
  access-violation failures (2), tests/unit/test_lang_primitives.py (1),
  tests/unit/strata/test_strata_core_gil.py (1).

ACCEPTANCE
- Each cluster above gets its own scoped leaf ticket under T-3505 (or is
  confirmed a duplicate of an existing one), with root cause confirmed
  from source, not guessed.
- Do not fix anything under this ticket directly -- it is a
  classification/filing ticket, per T-3076/T-3659's own established
  posture for tracking leaves in this epic.
