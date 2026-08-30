---
id: T-2568
title: 'may-raise resolver ignores a guard predicate that establishes a call''s precondition:
  all 8 remaining EXHAUST002 findings'
state: in-progress
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/_mayraise.py
- docs/modules/arch.md
- tests/unit/test_arch.py
- src/frob/arch/_python.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/arch/_mayraise.py
  reason: resolver module (scope was empty on ticket)
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/modules/arch.md
  reason: frob:doc target of touched symbols in _mayraise.py
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/unit/test_arch.py
  reason: unit tests for compute_may_raise
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/arch/_python.py
  reason: populates the new NormalizedCallArg.text field the resolver's guard-discharge
    needs
  actor: logan
  at: '2026-08-30'
designated_repro_test: null
acceptance:
- text: given a function that calls int() on a value guarded by an immediately preceding
    .isdigit() check, when compute_may_raise resolves it, then the leaked set does
    not name ValueError
  evidence: []
- text: given a function that calls int() on an unguarded string, when compute_may_raise
    resolves it, then the leaked set still names ValueError
  evidence: []
- text: given this repo's own source, when the exhaustive_handling gate runs unbudgeted
    with the gate cache bypassed, then the EXHAUST002 count is zero
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The third false-positive class in the may-raise resolver, found while
triaging T-2377's EXHAUST002 corpus and left unfixed deliberately -- it
needs guard-to-call flow, which is an analysis capability, not a table
edit like T-2552's was.

THE SHAPE. A predicate immediately before a call establishes that call's
precondition, and the resolver has no notion of it, so it reports the
exception the guard exists to exclude:

    for entry in proc_dir.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)        # EXHAUST002: ValueError escapes

`int()` genuinely raises `ValueError` on a non-numeric string. The guard
means this call site cannot see one. The resolver models the call, not
the guard, so the finding stands and the only ways to clear it are to
catch an exception that cannot occur or to declare `# frob:raises
ValueError` -- a declaration that would be false.

MEASURED. After T-2539 and T-2552 landed, and after T-2543's A2+A4 split
moved the subscript class to EXHAUST004, EXHAUST002 stands at 8 findings
on this repo's own source -- and ALL 8 are this class. Every one names
`ValueError`, and each carries a guard the resolver cannot see:

  scripts/_require_python.py::_required_version         `\d+` regex group
  scripts/fleet_status.py::_scan_for_live_worktree_process   .isdigit()
  scripts/fleet_status.py::lease_classification         (via the above)
  scripts/fleet_status.py::land_lock_holder_pids             .isdigit()
  src/frob/process/_reap.py::count_running_checks            .isdigit()
  src/frob/testing/_coverage_refresh.py::_available_memory_mb .isdigit()
  src/frob/tickets/_leases.py::scan_for_live_worktree_process .isdigit()
  src/frob/tickets/_leases.py::_scan_for_live_land_process    .isdigit()

WHY THIS TICKET MATTERS MORE THAN ITS COUNT. 8 findings is small, but it
is now the ENTIRE EXHAUST002 corpus. T-2377 cannot promote EXHAUST002 to
ERROR until these are zero, so this ticket is the last thing standing
between the family and its 1.0 severity decision. It should be sized on
that, not on the finding count.

TWO CANDIDATE DIRECTIONS, neither obviously right -- treat this as a
decision ticket first, the same way T-2543 was:

1. A narrow, curated guard->call table: `.isdigit()` on the same
   expression discharges `ValueError` from a following `int()`; a regex
   group from a numeric-only pattern likewise. Cheap and covers 8 of 8
   here, but it is a curated list and will not generalise -- the same
   objection that ruled out idiom-matching for T-2552's Class B.
2. Real local flow: extend the normalized model to carry local bindings
   and simple predicate narrowing, then let a guard discharge a
   contribution for the region it dominates. This is the same model
   extension T-2543's Class A option A5 needs (`NormalizedFunction`
   carries no local assignments at all today), so the two should probably
   be sequenced together rather than each half-building it.

DO NOT fix this by weakening `_BUILTIN_RAISERS` for `int`/`float`.
`ValueError` there is real and correctly reported at every unguarded
site; T-2552 removed `TypeError` only because a STRICTER gate (`ty`)
owns it, and no such second owner exists for `ValueError`.
