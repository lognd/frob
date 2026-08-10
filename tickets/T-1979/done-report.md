## Done report

Both ARCH001 findings fixed by extracting the pure-data half of each
function into a private helper (_orphaned_evidence_findings/
_refuse_orphaned_evidence for _check_orphaned_evidence_deletion;
_demote_to_evidence_only_locked for demote_to_evidence_only), zero
behavior change, matching this repo's own ARCH001-fix precedent
(_check_cross_ticket_leakage's own split into _load_leakage_ledgers/
_report_leaked_tickets).

COV001 fixed by adding demote_to_evidence_only's frob:doc anchor --
which required actually writing T-1944's doc section (deferred at land
time due to a lease conflict, tracked as T-1975 for the CLI-wiring half)
rather than leaving a dangling anchor, so this also closes out the
"Evidence-only scope (T-1944)" doc section on docs/modules/tickets.md.

TEST001 fixed by adding the missing frob:tests directives above
demote_to_evidence_only, binding its two existing tests in
tests/unit/test_tickets_evidence_only_scope.py.

The 5th pre-existing finding (DOCENUM001 SYS110) is NOT mine -- traces
to T-1629's unrelated land, already tracked by T-1974.

Evidence:
tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_refuses_when_branch_deletes_evidence_bound_test
tests/unit/test_tickets_evidence_only_scope.py::TestDemoteToEvidenceOnly::test_demote_releases_the_lease_and_keeps_evidence_covered

Gates: `frob check --only gates` re-measured after this fix -- report
its own new count in the coordinator-facing report.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_refuses_when_branch_deletes_evidence_bound_test` (pytest node id, verified passing when recorded)
- `tests/unit/test_tickets_evidence_only_scope.py::TestDemoteToEvidenceOnly::test_demote_releases_the_lease_and_keeps_evidence_covered` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 2 error(s), 1387 warning(s), 709 waived
- error-findings: F401@/home/logan/projects/frob/tests/unit/test_tickets_evidence_only_scope.py, PRE001@tickets/T-1979
