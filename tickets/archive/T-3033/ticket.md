---
id: T-3033
title: test_doctor.py times out under xdist contention (branch-scan cost)
state: done
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
- tests/test_doctor.py
- src/frob/doctor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_doctor.py::test_module_carries_heavy_subprocess_marker
- tests/test_doctor.py::test_run_diagnosis_reports_frob_version
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 2067a6f4af07154bc19b1bc4ed9c603377913b2d
---
Linux full-suite triage (T-2992): tests/test_doctor.py (13 tests) is
reliable in isolation, serial (`pytest tests/test_doctor.py -p no:xdist`:
13/13 pass) but reliably TIMES OUT under multi-agent contention with
xdist workers (`-n 2`/`-n 3`, this box's fleet running 3+ concurrent
agents): pytest-timeout's own 120s per-test budget fires mid-test, and
the xdist worker dies ("node down: Not properly terminated").

Root cause (thread dump captured at the timeout): the hung test is deep
in `frob.doctor.scan_stale_ticket_leases -> frob.tickets._reconcile.
reconcile -> frob.tickets._unlanded._unlanded_branch_work ->
_finished_signals_on_branch -> _ticket_states_on_branch ->
_ticket_states_on_ref -> frob.gitio.run_argv -> guarded_subprocess_run`,
i.e. a real `git` subprocess spawned once per branch while scanning
EVERY branch in this repo for stale ticket leases. This repo currently
has ~900+ branches (per an existing memory note on `frob ticket doable`
having the identical "scans every branch" cost, tracked toward T-2629).
Under CPU contention from sibling agents' own `frob check`/`cargo`/
pytest processes, the per-branch git spawn cost multiplies past the
120s per-test ceiling.

This is test-fragility SPECIFIC TO THIS DEVELOPMENT BOX's branch count
and contention level, not a Linux-general defect and not something
T-2980/T-2991 need to re-fix -- but it is a real, reproducible source of
flaky CI/local runs whenever a doctor-scan test lands in the same
xdist worker pool as other slow work, and the underlying "scan every
branch" cost is the same one already flagged for `frob ticket doable`
(T-2629 territory).

SUGGESTED FIX DIRECTIONS (not applied here):
  - Mark tests/test_doctor.py with the same `heavy_subprocess`/
    xdist_group treatment tests/conftest.py already gives OTHER
    real-git-heavy modules (see tests/conftest.py's own
    `pytest_collection_modifyitems`), so it runs serially on one worker
    instead of racing for CPU across several.
  - Or: bound `scan_stale_ticket_leases`'s branch enumeration cost
    directly (cache per-branch state, or cap tickets/day scanned),
    which would also help T-2629's `frob ticket doable` cost.