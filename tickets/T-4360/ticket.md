---
id: T-4360
title: Measure whether -n auto oversubscribes memory during frob_self_scan_heavy on
  Windows CI
state: queued
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- pyproject.toml
- .github/workflows/*.yml
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
T-4353 hardened xdist's LoadScopeScheduling against the KeyError:
<WorkerController gwN> scheduler race (a worker dying between add_node
and add_node_collection), so that race no longer takes down the whole
Windows suite. It did NOT establish, by measurement, why the workers
running frob_self_scan_heavy group tests (test_sys_gate_zero_violations,
test_checker_fleet_deploy_vet_have_no_undeclared_fs_write_selfaudit001)
died from suspected OOM in the first place on run 34298358489 -- both
died ~300s in, well under their @pytest.mark.timeout(1200) budget, with
no timeout dump, which the existing crash-cause inference already
labels "suspect OOM".

T-4329 eliminated the two-concurrent-full-repo-scans shape (fixture-
closure based heavy grouping). This run's evidence is consistent with
the group serializing correctly onto ONE worker at a time, but that
ONE worker plus the ambient `-n auto` (pyproject.toml addopts) load
still being too much for the Windows runner's memory -- i.e. Candidate
3 from T-4353's own ticket body: "a genuine memory ceiling where even
one scan plus normal parallel load is too much on this runner", not yet
distinguished by measurement from "another memory-hungry test outside
the group" or "the group overlapping something else scheduled
concurrently."

Establish which by MEASURING (not reasoning): capture available/peak
memory (e.g. a background sampler writing to a log, or Windows
perf-counter query) during an actual `winrun`-driven full-suite run
while the frob_self_scan_heavy group executes, cross-referenced against
which OTHER tests are running concurrently on other workers at that
wall-clock moment. If the memory-ceiling theory holds, the fix likely
needs a Windows-specific worker-count reduction (a
pytest_xdist_auto_num_workers hook, or a lower explicit -n for the
Windows CI step) rather than anything in tests/conftest.py -- hence
pyproject.toml/workflow scope, out of T-4353's tests/conftest.py-only
scope.

Not proof of anything until measured across multiple consecutive
Windows runs -- one completion has already been mistakenly called a fix
once for this exact defect (T-4329's own retraction). State the number
of consecutive completions treated as evidence before closing.