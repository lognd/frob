---
id: T-0545
title: 'gates: coverage/baseline/prework evidence chain is gitignored-local, untrusted
  by CI (B5)'
state: done
kind: bug
origin: auditor
created: '2026-07-21'
priority: medium
parent: T-0403
tier: ticket
sprint: null
scope:
- src/frob/gates/
- pyproject.toml
- CHANGELOG.md
- uv.lock
- frob.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: pyproject.toml
  reason: 'REL001: public API changed (write_coverage_lock/load_coverage_lock/coverage_lock_diff),
    requires version bump + changelog entry per project convention'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: 'REL001: public API changed (write_coverage_lock/load_coverage_lock/coverage_lock_diff),
    requires version bump + changelog entry per project convention'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: uv.lock reflects pyproject.toml's version bump; frob.lock is the doc-ack
    ledger updated for stamp_coverage's ack
  actor: logan
  at: '2026-07-21'
- op: add
  glob: frob.lock
  reason: uv.lock reflects pyproject.toml's version bump; frob.lock is the doc-ack
    ledger updated for stamp_coverage's ack
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_gates.py::TestTestGate::test_test012_missing_lock_warns
- tests/test_gates.py::TestTestGate::test_test012_drifted_module_warns
- tests/test_gates.py::TestTestGate::test_test012_matching_lock_is_clean
- tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_refreshes_committed_lock
- tests/test_gates.py::TestCoverageLoad::test_coverage_lock_diff_flags_drift_and_missing_module
designated_repro_test: null
threat: null
component: null
---
docs/audits/gates-accounting.md B5. coverage.xml, .frob/coverage-stamp, .frob/baseline, .frob/prework/*.json are all gitignored -- a fresh CI checkout has no stamp and no committed artifact any reviewer/CI can diff to verify a coverage claim. RIGHT-WAY fix direction: commit a signed/summary coverage artifact (hash + floors, not the raw xml) or fail closed in CI when the stamp's source_sha cannot be reproduced from a clean run, so TEST005/006 mean something externally verifiable.