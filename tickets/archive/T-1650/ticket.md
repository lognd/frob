---
id: T-1650
title: 'TEST005 burn-down: cross-package remainder (73 findings, T-1273 successor)'
state: done
kind: feature
origin: human
created: '2026-08-06'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/tickets/_leases.py
- tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_leases.py
  reason: 'T-1273 TEST005 remainder: fixing tickets/_leases.py branch-coverage gaps
    first'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_ticket_leases.py
  reason: 'T-1273 TEST005 remainder: fixing tickets/_leases.py branch-coverage gaps
    first'
  actor: logan
  at: '2026-08-06'
evidence:
- tests/test_ticket_leases.py::TestWarnIfWorktreeStaleFailureBranches::test_silent_when_main_ref_does_not_exist
- tests/test_ticket_leases.py::TestWarnIfWorktreeStaleFailureBranches::test_silent_when_rev_list_count_fails
- tests/test_ticket_leases.py::TestWarnIfWorktreeStaleFailureBranches::test_silent_when_count_is_not_numeric
- tests/test_ticket_leases.py::TestWarnIfWorktreeStaleFailureBranches::test_silent_when_config_lookup_raises
- tests/test_ticket_leases.py::TestLeaseAgeSecondsExceptionBranch::test_none_when_recorded_at_is_not_a_string
- tests/test_ticket_leases.py::TestRecordReleaseRenameLeaseErrorBranches::test_record_lease_degrades_on_mkdir_failure
- tests/test_ticket_leases.py::TestRecordReleaseRenameLeaseErrorBranches::test_record_lease_degrades_on_write_failure
- tests/test_ticket_leases.py::TestRecordReleaseRenameLeaseErrorBranches::test_release_lease_degrades_on_unlink_failure
- tests/test_ticket_leases.py::TestRecordReleaseRenameLeaseErrorBranches::test_rename_lease_degrades_on_malformed_old_record
- tests/test_ticket_leases.py::TestRecordReleaseRenameLeaseErrorBranches::test_rename_lease_degrades_on_write_failure
designated_repro_test: null
acceptance:
- text: GIVEN src/frob/tickets/_leases.py's record_lease/release_lease/rename_lease/warn_if_worktree_stale/lease_age_seconds
    WHEN their OS-failure and malformed-input branches are exercised THEN each degrades
    to a logged warning and Ok(None)/None as documented, verified by real behavioral
    tests bound via frob:tests, and the file's branch coverage (measured via a scoped
    pytest --cov run) rises from 60-74% per-symbol to above the 75% unit_branch_cov
    floor
  evidence:
  - tests/test_ticket_leases.py::TestWarnIfWorktreeStaleFailureBranches::test_silent_when_main_ref_does_not_exist
  - tests/test_ticket_leases.py::TestWarnIfWorktreeStaleFailureBranches::test_silent_when_rev_list_count_fails
  - tests/test_ticket_leases.py::TestWarnIfWorktreeStaleFailureBranches::test_silent_when_count_is_not_numeric
  - tests/test_ticket_leases.py::TestWarnIfWorktreeStaleFailureBranches::test_silent_when_config_lookup_raises
  - tests/test_ticket_leases.py::TestLeaseAgeSecondsExceptionBranch::test_none_when_recorded_at_is_not_a_string
  - tests/test_ticket_leases.py::TestRecordReleaseRenameLeaseErrorBranches::test_record_lease_degrades_on_mkdir_failure
  - tests/test_ticket_leases.py::TestRecordReleaseRenameLeaseErrorBranches::test_record_lease_degrades_on_write_failure
  - tests/test_ticket_leases.py::TestRecordReleaseRenameLeaseErrorBranches::test_release_lease_degrades_on_unlink_failure
  - tests/test_ticket_leases.py::TestRecordReleaseRenameLeaseErrorBranches::test_rename_lease_degrades_on_malformed_old_record
  - tests/test_ticket_leases.py::TestRecordReleaseRenameLeaseErrorBranches::test_rename_lease_degrades_on_write_failure
threat: null
component: null
---
T-1273's per-package children (T-1276..T-1313 and successors) all landed
and closed; the epic's package-level burn-down is substantially done.
A fresh, full unscoped `make coverage` run on 2026-08-06 (coverage.xml
joined 527 classes vs 477 in the committed frob-coverage.lock.json --
more, not fewer, so not deflated per TEST017/_DEFLATION_FLOOR) shows 73
TEST005 findings remain, scattered thinly across many packages rather
than concentrated in any one still-open child:

gates=14 tickets=10 app=10 serve=9 arch=8 scaffold=5 refactor=5
testing=3 vet=2 strata=2 mutate=2 dup=1 doctor.py=1 gitio.py=1

None are at 0.0% branch coverage (the dead-code-risk priority tier this
epic called out) -- every finding here is a partially-tested symbol
sitting somewhere between ~11% and ~74%, below the 75/70 floors. This
ticket is the honest remainder: burn these down to zero with real
behavioral tests (never assert-True filler), the same discipline every
prior child in this epic used.

Note: the coverage run that produced these numbers had one unrelated
pre-existing failure (tests/unit/test_exports.py::
TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols)
that blocked make coverage's own promote-to-committed step (T-1363 guard);
the data was recovered from .frob/coverage.partial.xml per playbook
section 6d and is a real full-suite run (8571 collected), not a subset.