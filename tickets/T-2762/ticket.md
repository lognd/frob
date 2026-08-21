---
id: T-2762
title: Reproduce/fix xdist contention for 4 real-repo build_graph tests found by T-1654
  audit
state: in-progress
kind: bug
origin: human
created: '2026-08-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/conftest.py
evidence_scope:
- tests/unit/test_conftest_stackdump.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/conftest.py
  reason: 'T-2762: reproduce/fix xdist contention for 4 real-repo build_graph tests;
    the only mechanical fix location is _SELF_SCAN_HEAVY_NAME_SUBSTRINGS in tests/conftest.py'
  actor: logan
  at: '2026-08-20'
evidence:
- tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping::test_self_scan_heavy_tests_share_one_xdist_group
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-1654 audited the six files T-1433/T-1635 flagged as unaudited for the
`build_graph(real repo root, ...)` xdist self-scan contention shape
(`.frob/derived.lock` unbounded `fcntl.flock` contention plus full-repo
peak-memory cost under `pytest-xdist -n auto`). Denominator: 6 files
(`tests/test_waive_gate.py`, `tests/test_graph.py`, `tests/test_dup.py`,
`tests/test_gates.py`, `tests/test_secrets_gate.py`, `tests/test_vet.py`),
every `build_graph`/`find_clones` call site in each read directly (not
grep-inferred).

Result: 4 of the 6 files have ZERO real-repo-root `build_graph` calls --
every `build_graph`/`find_clones` invocation in `tests/test_graph.py`,
`tests/test_dup.py`, `tests/test_secrets_gate.py`, and `tests/test_vet.py`
targets an isolated `tmp_path` fixture (copying real source files into it
where a real-source comparison is needed, same isolation pattern the
already-safe tests in the other files use). These 4 files are CLEAR.

The other 2 files have 4 candidate tests total, all sharing the exact
same shape T-1635 fixed (`build_graph`/`_load_inputs`/`_snapshot` called
directly against `Path(__file__).resolve().parents[1]`, no tmp_path
isolation available because the test verifies something about the real
repo itself):

- tests/test_waive_gate.py::TestWaive006RealRepo::test_zero_errors_on_real_repo
- tests/test_waive_gate.py::TestWaive007RealRepo::test_zero_findings_on_real_repo
- tests/test_gates.py::TestProtocolSummaryGate::test_real_repo_scan_runs_end_to_end_without_crashing
- tests/test_gates.py::TestOptInGates::test_the_preexisting_rapid_sweep_waiver_now_actually_suppresses

A scoped run of these 4 together under `pytest -n 2 --dist loadscope`
(no grouping applied) completed without a node-down/timeout, but
confirmed all 4 are genuinely heavy full-repo scans: 66.01s, 28.64s,
23.28s, 19.46s respectively (`--durations=10`). This is the same
timing profile T-1635's own fix targeted, but it is NOT the same
evidentiary bar T-1635 used to justify its addition to
`_SELF_SCAN_HEAVY_NAME_SUBSTRINGS` -- T-1635's own comment in
tests/conftest.py records reproducing an actual pytest-timeout trip
plus a faulthandler trace showing a worker blocked inside
`derived_state_lock`/`derived_state_write_lock` under a REAL
`pytest -n auto` FULL-SUITE run. A 4-test, 2-worker scoped run (all I
can run inside a dispatched sub-agent's foreground timeout budget, per
docs/guides/agent-playbook.md section 3c) cannot reproduce that --
genuine contention needs many concurrent full-repo scans queueing on
the same worker pool alongside the rest of the suite, which is a
COORDINATOR-only verification (section 3c/6b), not something a
sub-agent can run.

ACTION for whoever picks this up: run a real `pytest -n auto` full-suite
pass (or a heavy-load repro harness) with these 4 node ids present, and
capture a faulthandler dump if a worker goes down. If it reproduces the
same `derived_state_lock` contention, add all 4 names' distinguishing
substrings to `_SELF_SCAN_HEAVY_NAME_SUBSTRINGS` in tests/conftest.py
(the mechanism is a straightforward substring append, no other code
changes needed) with a comment following the T-1635 precedent. If it
does NOT reproduce, close this out with that negative result recorded
instead of adding speculative names.
