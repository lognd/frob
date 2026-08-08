---
id: T-1366
title: CI still cannot verify the .frob/-local coverage stamp and delta baseline (T-1265
  successor)
state: done
kind: security
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- .github/workflows/ci.yml
- src/frob/gates/_coverage.py
- src/frob/gates/_baseline.py
- tests/test_gates.py
- tickets/**
- rapid-debt.jsonl
- design/frob.strata
- docs/design/registry/check-coverage.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: regression test for is_stamp_stale belongs beside test_stamp_coverage_roundtrip
    / the is_baseline_stale sibling tests in this file
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/**
  reason: same ledger/rapid-debt bookkeeping shards accumulated across my worktree's
    prior tickets in this session, implicitly in scope for every ticket the same way
    tickets.md is -- precedent T-1817/T-1818
  actor: logan
  at: '2026-08-08'
- op: add
  glob: rapid-debt.jsonl
  reason: same ledger/rapid-debt bookkeeping shards accumulated across my worktree's
    prior tickets in this session, implicitly in scope for every ticket the same way
    tickets.md is -- precedent T-1817/T-1818
  actor: logan
  at: '2026-08-08'
- op: add
  glob: design/frob.strata
  reason: frob sys sync-interface auto-writes this file when a new public gates symbol
    (is_stamp_stale) is added; required to clear SELFAUDIT001
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: 'land refused: CHK-THEME-GITIGNORED-TRUST cites T-1366 as its live tracker
    via disposition deferred:T-1366; T-1366 IS the fix, must re-point in this same
    change'
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_gates.py::TestCoverageLoad::test_stamp_not_stale_when_files_unchanged
- tests/test_gates.py::TestCoverageLoad::test_stamp_stale_when_file_changes
designated_repro_test: null
acceptance:
- text: GIVEN a CI run WHEN the coverage stamp or delta baseline is absent, stale
    or tampered THEN the build fails rather than silently degrading to a pass
  evidence:
  - tests/test_gates.py::TestCoverageLoad::test_stamp_stale_when_file_changes
threat: repudiation
component: null
---
T-1265 made the ci.yml self-gate blocking and added a TEST012 check for frob-coverage.lock.json, the one committed coverage channel. The residue it did not close: the coverage stamp and the delta baseline still live in .frob/, which is gitignored and never restored in CI, so TEST005/TEST006 remain structurally inert there. CHK-THEME-GITIGNORED-TRUST in docs/design/registry/check-coverage.yaml is repointed here.