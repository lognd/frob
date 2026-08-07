---
id: T-1354
title: Investigate xdist coverage-merge dropping worktree_runner branch data (false
  TEST005 0.0%)
state: dropped
kind: bug
origin: human
created: '2026-07-31'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_coverage.py
- Makefile
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1276 (TEST005 burn-down: src/frob/app) found a false-positive 0.0%-branch
TEST005 finding for `src/frob/app/worktree_runner.py::run`. A direct,
non-xdist `pytest --cov=frob.app.worktree_runner --cov-branch` run against
its existing dedicated test
(tests/test_ticket_leases.py::TestWorktreeSweepCli::test_sweep_cli_prints_verdicts_and_summary)
measures 80% real branch coverage -- but the full-suite `make coverage`
run (xdist-parallel, T-1320's fresh stamp) attributes this symbol 0.0%.

<!-- frob:waive DOC006 reason="'src/demo/__init__.py' names a stale phantom entry that T-1320's Done report found INSIDE a corrupted coverage.xml merge, not a real tracked source file -- it never existed in the repo tree; the whole point of the incident note is that this path should not have been there" -->
This looks like the same coverage-merge class T-1320's Done report flagged
for `coverage xml` (stale `src/demo/__init__.py` entry breaking the
combined-data merge) and TEST011 already partially detects
(`module_join_fraction` / `stale_by_mtime`) -- but TEST011 did not fire
for this file, so whatever is dropping this symbol's xdist-worker data
during the full-suite merge is a distinct, undetected case.

Work: investigate why `src/frob/app/worktree_runner.py`'s coverage data is
lost during the full-suite xdist coverage merge despite a passing,
directly-verified dedicated test; either fix the merge, or extend
TEST011's detection to catch this class of false 0.0% so a burn-down
ticket does not spend effort re-testing already-covered code.

## Drop reason
- 2026-08-01: investigated directly (scoped xdist repro of the cited test showed 80 pct, matching the direct-run number, no merge defect reproduced) -- the false 0.0 pct is best explained by T-1353's already-mitigated node-down worker-crash class at full-suite scale, not a distinct code defect in src/frob/gates/_coverage.py's merge/attribution logic; extending TEST011 to catch this class filed as its own follow-up (T-1389), not forced into this investigation ticket