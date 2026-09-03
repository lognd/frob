---
id: T-3532
title: Two frob_self_scan_heavy waiver tests still run private whole-repo scans outside
  the T-3495 shared artifacts
state: done
kind: bug
origin: agent
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_coordinator_scripts.py
- tests/test_gates.py
- tests/conftest.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: declare no-behavior-change for BUG002/TEST016
  actor: logan
  at: '2026-08-31'
  old_length: 1594
  new_length: 1949
evidence:
- tests/unit/coordinator_suite/test_fleet_report.py::TestFleetStatusLarge001WaiverParses::test_waiver_still_suppresses_large001
- tests/gates_suite/test_run.py::TestOptInGates::test_the_preexisting_rapid_sweep_waiver_now_actually_suppresses
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 47fcfa898ded38b3a7a61b8da25c6ce19895badc
---
MEASURED on run 33353658750 (macos-latest, completed, 5 failures): all 3
faulthandler "Timeout (0:01:40)" dumps in the log are on PASSING tests --
pure noise (T-3531 raises the threshold). But the dump contents show a real
T-3495 residue: two dumps are the shared frob_self_scan_artifacts fixture
computing (expected, slow runner), while the third is
tests/unit/test_coordinator_scripts.py::test_waiver_still_suppresses_large001
running its OWN full repo scan (arch_gate -> _check_abstraction_opportunities,
scan_file_capabilities) OUTSIDE the shared fixture. Its sibling
tests/test_gates.py::test_the_preexisting_rapid_sweep_waiver_now_actually_suppresses
has repeatedly appeared in earlier tail dumps too (runs 33336905168,
33303586303). Both are members of the frob_self_scan_heavy xdist group but
never adopted the T-3495 shared artifacts, so each still pays a private
multi-minute whole-repo scan at the tail on 3-4 core runners.

FIX: route both tests onto the session-scoped shared scan where their
assertions allow it -- if a test's subject is the WAIVER SUPPRESSION logic
rather than the scan itself, it should consume the shared artifacts (or a
scoped fixture-repo scan) instead of re-scanning the live repo. If a test
genuinely must run its own live-repo scan, say why in its docstring and
leave it -- but measure first: `time` each under -p no:xdist before/after.
MUST-STAY-QUIET: both tests still fail on a planted unsuppressed finding.
ACCEPTANCE: neither test appears in faulthandler dumps on the next two CI
runs; group tail wall time drops on a quiet local box (state numbers).

frob:no-behavior-change reason="routes both tests onto shared/scoped graph builds for wall-time/cost, not correctness; both tests assert the identical waiver-suppression behavior before and after and already passed at the parent commit -- this is a performance/plumbing fix, not a behavior fix, so BUG002 genuinely cannot require a fail-then-pass repro"
