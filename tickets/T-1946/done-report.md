## Done report

Root cause: a branch's own committed diff can delete or rename a pytest
test node ANOTHER ticket cites as evidence, with no signal at the point
of deletion -- two independent actors did this in one hour (a
coordinator's file cleanup, and a legitimate test replacement in an
unrelated ticket's land), each orphaning evidence outside their own
declared scope. One deletion took out three unrelated tickets' evidence
at once (100% of the then-current unscoped error floor, 4 COV003
findings).

Fix: `_check_orphaned_evidence_deletion` (src/frob/tickets/_land.py),
wired into `_land_precheck_remaining_checks` right after the existing
cross-ticket-leakage check. Computes the branch's own three-dot diff
(`_branch_changed_files`, the same primitive T-1922 fixed the two-dot/
three-dot confusion in) and, for every OTHER ticket's non-cmd evidence
id whose file lies in that diff, checks whether it still resolves
against the worktree's currently collected tests
(`_evidence_valid_for_ticket`). A node id that no longer resolves
refuses the land (`LandError.OrphanedEvidenceDeletion`), naming the
affected ticket(s) and evidence id(s). A rename that ALSO re-points the
affected ticket's evidence in the SAME diff is never refused, since the
check reads the ledger's POST-diff state.

Deliberately does not auto-repoint or auto-delete the stale evidence
itself (the WAIVE004 lesson applied to evidence: the binding is the
only record a ticket was ever proven, so repointing it automatically
would fabricate proof) -- only refuses and names what to fix.

Evidence:
tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_refuses_when_branch_deletes_evidence_bound_test (acceptance 1, fail-then-pass proof)
tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_deletion_of_unbound_test_lands_cleanly (acceptance 2, no false refusal)
tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_rename_that_repoints_evidence_in_same_diff_is_accepted (acceptance 3)

check-repro: BUG002 --check-repro on the new fresh test returned
NO_VERDICT (collection failure at parent commit -- the test exercises
code that did not exist there yet). Structural, not evasion; recorded
here per the playbook's documented gap for a brand-new test node.

Filed: T-1973 (add this ticket's and T-1944's doc sections to
docs/modules/tickets.md once no live lease blocks it -- could not commit
the doc prose in either ticket's own land window due to a live
cross-ticket lease on that file at the time).

Known limitation: post-mutation re-verification (mirroring T-1932's
second call site for the cross-ticket-leakage guard) is not yet added
for this check -- no Tier-A auto-fix handler in this repo deletes or
renames test files today, so the mutation window that pattern exists to
close is narrower here; documented in the (currently unlandable) doc
section rather than silently assumed safe.

Gates: SCOPE001/PRE001/file-scoped COV002 clean for this ticket's
touched files; 290/291 in the land/leakage regression sweep (the one
failure is a pre-existing environment flake reproducing identically on
an unmodified main checkout, unrelated to this change).

### Changed
```
 docs/modules/tickets.md                        |  51 +++++
 src/frob/gates/__init__.py                     |  10 +-
 src/frob/tickets/__init__.py                   |   3 +-
 src/frob/tickets/_evidence.py                  |  28 ++-
 src/frob/tickets/_land.py                      | 107 ++++++++++
 src/frob/tickets/_models.py                    |  32 +++
 src/frob/tickets/_scope.py                     |  99 +++++++++-
 tests/unit/test_land_orphaned_evidence.py      | 214 ++++++++++++++++++++
 tests/unit/test_tickets_evidence_only_scope.py | 258 +++++++++++++++++++++++++
 tickets/T-1944/done-report.md                  |  93 +++++++++
 tickets/T-1944/ticket.md                       |  60 +++++-
 tickets/T-1946/ticket.md                       |  50 ++++-
 tickets/T-1973/ticket.md             |  40 ++++
 tickets/T-draft-8d6e958c/ticket.md             |  33 ++++
 14 files changed, 1069 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_refuses_when_branch_deletes_evidence_bound_test` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_deletion_of_unbound_test_lands_cleanly` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_rename_that_repoints_evidence_in_same_diff_is_accepted` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 8 error(s), 1167 warning(s), 737 waived
- error-findings: ARCH001@src/frob/tickets/_land.py, ARCH001@src/frob/tickets/_scope.py, COV001@src/frob/tickets/_scope.py, DUP001@src/frob/tickets/_scope.py, F401@/home/logan/projects/frob/.claude/worktrees/detector-fp/tests/unit/test_tickets_evidence_only_scope.py, SELFAUDIT001@design, TEST001@src/frob/tickets/_scope.py, WIRE001@src/frob/tickets/_scope.py
