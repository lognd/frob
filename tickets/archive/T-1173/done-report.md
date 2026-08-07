## Done report

Fixed the bug: `renumber_one`'s draft-to-final id rewrite (called by
`finalize_draft`/`finalize_draft_for_land`, i.e. every `frob ticket land`)
rewrote the ledger and every code reference to the ticket's id, but never
touched the cross-worktree lease file (T-0473's
`<git-common-dir>/frob-leases/<ticket-id>.json`) -- left behind under the
OLD draft id, so the same worktree that had just renumbered its own
ticket looked lease-less to `frob check --ticket <final-id>` immediately
afterward.

Added src/frob/tickets/_leases.py::rename_lease(root, old_id, new_id):
migrates the lease file to the new id's path AND rewrites the record's
own `ticket_id` JSON field (a bare filesystem rename alone would leave
the stale id embedded in the body, which read_all_leases trusts over the
path it parsed from). Missing old-id lease is a no-op (mirrors
release_lease's tolerance); a git-dir/read/write failure degrades to a
logged warning, never fails the renumber.

Wired into src/frob/tickets/_new_renumber.py::_finish_renumber (the
single tail shared by renumber_one's persist path, which finalize_draft/
finalize_draft_for_land both delegate through) -- runs strictly AFTER
the ledger persist succeeds, so a persist failure never leaves a lease
renamed to an id the ledger itself never actually claimed.

Regression tests with real draft+lease fixtures (git worktree, off-
default-branch new_ticket mints a draft id, transition to IN_PROGRESS
records the lease, then renumber_one/finalize_draft_for_land renumbers
it in that SAME worktree -- exactly the T-1172-close incident shape):
TestRenumberMigratesLeaseEndToEnd covers both call paths. TestRenameLease
unit-tests rename_lease directly (content-field rewrite, missing-lease
no-op).

Updated docs/modules/tickets.md's "Cross-worktree lease side-channel
(T-0473)" section with a new paragraph and its "Public API" renumber_one
entry, plus design/frob.strata's tickets_ledger/testsuite interface
registries (rename_lease, TestRenameLease,
TestRenumberMigratesLeaseEndToEnd) -- both needed to clear AFFECT001/
SELFAUDIT001.

Filed: none.
Gates: frob check --ticket T-1173 clean (0 errors, 552 warnings, 682
waived) after ruff format on the three touched files. frob test --base
main: exit 0.

### Changed
```
 tickets.md | 33 +++++++++++++++++++++++++++++++--
 1 file changed, 31 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestRenameLease::test_rename_migrates_the_lease_file_and_updates_its_ticket_id_field` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRenameLease::test_rename_is_a_no_op_when_no_lease_exists_for_old_id` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRenumberMigratesLeaseEndToEnd::test_renumber_one_migrates_the_lease_the_worktree_still_holds` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRenumberMigratesLeaseEndToEnd::test_finalize_draft_for_land_migrates_the_lease_the_worktree_still_holds` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 552 warning(s), 682 waived
- error-findings: none (measured, zero errors)
