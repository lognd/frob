---
id: T-1375
title: frob-coverage.lock.json was rewritten during a session where no run stamped
  it
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_coverage.py
- tests/test_gates.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: need a regression test for the new audit-log provenance mechanism
  actor: logan
  at: '2026-08-01'
- op: add
  glob: docs/modules/gates.md
  reason: AFFECT001 requires updating the public-api doc for the new load_lock_audit_log
    function and write_coverage_lock's audit-trail behavior
  actor: logan
  at: '2026-08-01'
evidence:
- tests/test_gates.py::TestCoverageLoad::test_write_coverage_lock_records_an_audit_entry
- tests/test_gates.py::TestCoverageLoad::test_write_coverage_lock_audit_log_appends_across_calls
- tests/test_gates.py::TestCoverageLoad::test_load_lock_audit_log_missing_file_returns_empty
designated_repro_test: null
acceptance:
- text: GIVEN a session WHEN frob-coverage.lock.json changes THEN the write is attributable
    to an explicit stamp_coverage call that succeeded
  evidence:
  - tests/test_gates.py::TestCoverageLoad::test_write_coverage_lock_records_an_audit_entry
  - tests/test_gates.py::TestCoverageLoad::test_write_coverage_lock_audit_log_appends_across_calls
  - tests/test_gates.py::TestCoverageLoad::test_load_lock_audit_log_missing_file_returns_empty
threat: null
component: null
---
Observed 2026-08-01. After two make coverage runs that BOTH failed and both logged 'leaving coverage.xml, .frob/coverage-stamp, and frob-coverage.lock.json untouched (T-1363)', the working tree nevertheless showed frob-coverage.lock.json modified with 77 changed floors, several ratcheting sharply UP (src/frob/app/doctor_runner.py 0.0 -> 68.8, check_runner.py 21.6 -> 45.7, _daemon_proxy.py 22.5 -> 41.3). Neither run's log contains a 'stamp_coverage: stamped' or 'write_coverage_lock: locked N module(s)' line, and the only caller of write_coverage_lock is stamp_coverage, which the recipe skips on a nonzero status. So either a write path exists that does not log, or something outside the recipe (a concurrent agent worktree, a land, a plain frob check) can reach the ROOT lock. Either way the file changed without an attributable, logged, successful stamp -- which is exactly the trust property T-1363 was supposed to establish. The observed content was preserved for comparison at scratchpad/lock-unknown-provenance.json; the working copy was reverted rather than committed. NOTE the up-ratchets match the T-1354 false-0.0% symptom, so the data may well be GOOD -- the defect is that its provenance cannot be established, not necessarily its values.