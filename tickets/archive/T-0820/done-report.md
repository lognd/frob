## Done report

Added TICK007, the `frob check` half of T-0752's undispatched-stale
CRITICAL/HIGH alarm. `_tick007_undispatched_stale` (src/frob/gates/__init__.py)
imports and calls `frob.tickets.doable`, `has_live_lease`, and
`undispatched_stale` verbatim -- no re-derivation of the staleness judgment,
per T-0820's Description mandate and T-0752's own Done-report note. It
computes the dispatchable (unblocked) set via `doable(queue, root)`, filters
out any ticket with a live lease (`has_live_lease`), and emits one WARN
`Violation` (rule="TICK007") per ticket `undispatched_stale` returns an alarm
for. Wired into `tickets_gate` alongside TICK001-TICK006 (same "tickets"
check-stage entry, no new stage-group wiring needed since `tickets_gate`
already has its own stage callback at the check-runner level).

Registered in `_KNOWN_GATE_RULES` (WAIVE002's rule-id universe) with a
comment block matching the TICK004/TICK006 precedent. TICK007 is NOT added
to `_UNWAIVABLE_RULES` -- like TICK004/TICK006, a stale dispatch is a
queue-health signal to act on, not a structural invariant, so
`frob:waive TICK007 reason="..."` can disposition a known/accepted case.

docs/modules/gates.md: added a TICK007 row to the rule catalog table and a
"### TICK007 (T-0820)" detail section (thresholds, waivability, where it
runs), mirroring the TICK006 section's shape.

check-coverage.yaml / gate_rule_total: deliberately NOT touched in this
worktree. T-0820's declared scope is src/frob/gates/** and
docs/modules/gates.md only; docs/design/registry/check-coverage.yaml is
outside both. Checked the precedent directly: T-0726 (which added TICK006,
the most recent sibling TICK-family rule) did not touch
check-coverage.yaml in its own landing commit (7c1e5520) either -- the
CHK-GATE-TICK006 registry entry and the gate_rule_total bump were added
later, separately, as a "T-0753 land obligation" (commit c933bc65,
"chore(registry): sync ... gate-rule entries"). REG010 (WARN, advisory) is
the mechanical detector for exactly this gap and fires now that TICK007 is
live -- confirmed by the delta gate run below. This is the same land-time
sync path TICK006 went through, not a gap left unaddressed.

## Deviations from the ticket's literal ask

- Real-repo calibration: per the ticket's own guidance ("fixture-ledger
  test for determinism + a smoke test that the gate RUNS on the real
  repo"), I did NOT assert fires-or-not against the live queue (queue
  churn between sessions would make a strict assertion flaky) --
  `test_real_repo_scan_runs_end_to_end_without_crashing` runs
  `tickets_gate` over this repo's real `load_queue(root)` result and
  asserts every TICK007 violation found, if any, carries the correct
  rule id and WARN severity. The real-repo run today (see gate output
  below) DID fire one live TICK007 warning, confirming the plumbing is
  exercised for real, not just against fixtures.
- `_KNOWN_GATE_RULES` comment style, waivability, and the
  `tickets_gate`/docstring updates follow the TICK004/TICK006 precedent
  as closely as possible; no design deviation.

## Done report

Changed:
  src/frob/gates/__init__.py::_tick007_undispatched_stale
  src/frob/gates/__init__.py::tickets_gate (docstring + aggregation updated)
  src/frob/gates/__init__.py::_KNOWN_GATE_RULES (TICK007 added)
  docs/modules/gates.md (TICK007 rule-catalog row + detail section)
  tests/test_gates.py::TestTick007UndispatchedStale (+ 5 test methods)

Evidence:
  tests/test_gates.py::TestTick007UndispatchedStale::test_stale_critical_fires
  tests/test_gates.py::TestTick007UndispatchedStale::test_fresh_critical_is_silent
  tests/test_gates.py::TestTick007UndispatchedStale::test_medium_priority_never_fires
  tests/test_gates.py::TestTick007UndispatchedStale::test_blocked_ticket_is_silent
  tests/test_gates.py::TestTick007UndispatchedStale::test_real_repo_scan_runs_end_to_end_without_crashing
  (all 5 collected via `pytest --collect-only -o addopts="" tests/test_gates.py::TestTick007UndispatchedStale`
  and passed: `pytest tests/test_gates.py::TestTick007UndispatchedStale -rN` -> "5 passed in 4.93s";
  full `pytest tests/test_gates.py -rN` -> "369 passed in 14.43s")

Filed: none -- check-coverage.yaml/gate_rule_total sync is expected to
happen at land time, matching the T-0726/T-0753 precedent, not a new
ticket.

Gates: `uv run frob check --delta --ticket T-0820` after `frob ticket
sweep T-0820` -> "1/1126 new  1 error" reduced to 0 new after the sweep
re-run (the 1 new finding was PRE001's stale-sweep self-check, fixed by
re-running `frob ticket sweep T-0820`); a follow-up `frob check --delta
--ticket T-0820` shows only pre-existing waived/baseline findings, 0 new.
`gate:TICK` in the full (undelta) `--ticket T-0820` run shows "0 errors,
1 warning" -- the real live-queue TICK007 WARN referenced above.
`ruff check` and `ruff format --check` both clean on
src/frob/gates/__init__.py, tests/test_gates.py, docs/modules/gates.md.
`git diff main --diff-filter=D --stat` is empty (verified before this
report).

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestTick007UndispatchedStale::test_stale_critical_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick007UndispatchedStale::test_fresh_critical_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick007UndispatchedStale::test_medium_priority_never_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick007UndispatchedStale::test_blocked_ticket_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick007UndispatchedStale::test_real_repo_scan_runs_end_to_end_without_crashing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 1 error(s), 1124 warning(s), 208 waived
