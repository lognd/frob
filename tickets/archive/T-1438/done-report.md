## Done report

frob ticket close's BUG002/mutation-evidence check
(_close_mutation_evidence_for_ticket) passed current_branch(root) as the
diff/repro base ref. In a dispatched worktree agent's normal flow this
resolves to the WORKTREE'S OWN branch, which by close time already
carries the ticket's own fix commit at its tip -- _bug_repro_outcome_at_ref
then checked out that branch's tip (the fix itself) instead of the
pre-fix parent, so the designated repro test trivially "passed at parent"
for every bug-kind ticket, forcing --skip-mutation-evidence on every
single close.

Fix: added a public frob.gitio.merge_base(root, base) wrapper (over the
existing private _merge_base, the same computation working_diff already
performs), and changed _close_mutation_evidence_for_ticket to accept a
base_ref parameter (default "main", threaded from cfg.ticket_base_ref)
and resolve the git merge-base of HEAD against it, passing that resolved
commit -- not the branch name -- to mutation_evidence_violations and
bug_repro_violations.

Verified land's own precheck (_land_precheck / _resolve_main_branch_for_land)
does NOT share this defect: there `root` is the actual main checkout being
landed INTO (not the ticket's own branch), so current_branch(root)
correctly resolves to main itself.

Added a regression test (test_ticket_close_bug002_t1438.py) that builds a
real git repo with a main branch and a feature branch carrying a second
commit, then asserts the ref reaching mutation_evidence_violations/
bug_repro_violations is main's tip (the merge-base), never the feature
branch's own tip/name. Also covers the merge-base-unresolvable case
(non-git tmp_path) still degrading to None (skip), not a false verdict.

Docs updated in docs/modules/tickets.md (BUG002/close section) and
docs/modules/testing.md (new merge_base public symbol).

### Changed
```
 docs/modules/testing.md                      |  10 ++
 docs/modules/tickets.md                      |  23 ++++-
 src/frob/app/ticket_runner/_close_cmd.py     |  51 ++++++----
 src/frob/gitio.py                            |  13 +++
 tests/unit/test_ticket_close_bug002_t1438.py | 140 +++++++++++++++++++++++++++
 tickets.md                                   |   8 +-
 6 files changed, 225 insertions(+), 20 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_close_bug002_t1438.py::TestCloseMutationEvidenceBaseRef::test_uses_merge_base_not_own_branch_tip` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_close_bug002_t1438.py::TestCloseMutationEvidenceBaseRef::test_still_skips_when_merge_base_unresolvable` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_close_bug002_t1427.py::TestCloseRefusesBug002ShapeEndToEnd::test_close_refuses_when_evidence_passes_at_parent` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_close_bug002_t1427.py::TestCloseRefusesBug002ShapeEndToEnd::test_close_succeeds_when_evidence_fails_at_parent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 6 error(s), 392 warning(s), 693 waived
- error-findings: COV001@src/frob/gitio.py, OPAQUE001@tests/unit/test_ticket_close_bug002_t1438.py, PRE001@tickets/T-1438, SELFAUDIT001@design, WIRE001@src/frob/gitio.py, WIRE001@tests/unit/test_ticket_close_bug002_t1438.py
