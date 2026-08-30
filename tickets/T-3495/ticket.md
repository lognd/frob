---
id: T-3495
title: frob_self_scan_heavy serial chain rebuilds the same repo scan six times; share
  one session-scoped scan so the CI tail stops flapping
state: queued
kind: bug
origin: agent
created: '2026-08-30'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/conftest.py
- tests/system/test_frob_self_model.py
- tests/unit/strata/test_sys003_calibration.py
- tests/test_gates.py
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
STRUCTURAL CAUSE of the recurring ubuntu 99% tail stall, measured across
runs 33284942175/33289332473/33303586303/33336905168 (stall, ~18-19 min at
99%, budget kill) versus 33298117154/33308245923/33311990183 (complete,
16-17 min): tests/conftest.py:167 puts the six whole-repo self-scan tests
(tests/system/test_frob_self_model.py x4, tests/unit/strata/
test_sys003_calibration.py::test_sys003_zero_against_live_repo_design,
tests/test_gates.py::test_the_preexisting_rapid_sweep_waiver_now_actually_suppresses)
into one xdist_group ("frob_self_scan_heavy") -- deliberate, OOM-driven
(T-1472/T-1484 era: parallel full-repo scans OOM'd the runner). The group
therefore runs SERIALLY on one worker at the very end of the run: six
full-repo scans back to back, each independently rebuilding the same
graph/selfconform artifacts for the same tree. When each scan stays under
~160s the tail fits inside the budget; when repo growth pushes any past
the 300s per-test timeout, the timeout kills the worker, xdist re-queues
the test on a fresh worker (cold caches), and the cascade eats 18+ minutes
-- the run's completion is a coin flip on scan cost, which is why the
stall recurs after every land that grows the scanned population (T-3465,
T-1691, T-1601...). T-3458 (via-glob cache) and T-3478 (lock narrowing)
each bought headroom that growth then consumed.

FIX (the durable one): make the six tests share ONE scan per session
instead of six. Options, prefer (a):
 a. A session-scoped pytest fixture (scoped to the xdist worker running the
    group -- session scope suffices since the group pins to one worker)
    that builds the graph + runs check_self_conformance ONCE on the real
    repo and hands each test the artifacts; each test keeps its own
    assertions. The tests currently each call build_graph/sys_gate
    directly -- refactor them onto the fixture.
 b. Split the group across 2-3 workers (xdist_group per test pair) with a
    memory gate -- rejected unless (a) is infeasible: OOM risk returns.
 c. Raise the per-test timeout for exactly this group -- treats the
    symptom; acceptable only as a stopgap alongside (a).
MUST-STAY-QUIET: each test still fails independently on a planted
violation (the shared artifacts must not mask per-test assertions).
MUST-FIRE: a planted SYS100 violation still fails test_sys_gate_zero_violations
when the artifacts come from the shared fixture.
ACCEPTANCE: the frob_self_scan_heavy group's total wall time on a quiet
box drops to roughly one scan's cost plus assertion overhead (state the
before/after), and the next three consecutive ubuntu runs complete.
