## Done report

T-1550: `_committed_waive_deletions`/`_committed_out_of_scope_waive_deletions`
(src/frob/tickets/_land_git_ops.py) and `_check_committed_waive_deletions`
(src/frob/tickets/_land.py) now diff the branch's committed history against
`main_branch`'s LIVE tip instead of the stale `merge_base` captured before
any sibling ticket on the same shared worktree branch had landed. A
deletion an already-landed sibling committed is, by the time it lands,
already reflected on `main_branch` itself (squash-apply carries the whole
diff there) -- diffing from the live tip means that specific line shows no
delta on either side and is never re-discovered, with no ancestry walk or
commit-to-ticket message parsing required. A deletion still only present
on the worktree branch (not yet landed by anyone) is unaffected and still
refuses exactly as before. New regression test
`TestCommittedWaiveDeletionRefusal::test_already_landed_sibling_deletion_on_shared_worktree_not_recounted`
reproduces the T-1225/T-1444 shape directly: ticket A declares and lands
(real, non-dry-run) an out-of-scope waiver deletion; ticket B, continuing
on the same worktree branch with no re-merge of main, previously got
refused re-attributing A's already-landed deletion to itself -- now lands
clean.

### Changed
```
 tickets.md | 40 +++++++++++++++++++++++++++++++++++++++-
 1 file changed, 39 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_already_landed_sibling_deletion_on_shared_worktree_not_recounted` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_committed_out_of_scope_undeclared_waive_deletion_refuses_before_merge` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_committed_in_scope_waive_deletion_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_merge_base_drift_deletion_on_main_side_not_counted` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_branch_merges_main_after_main_deletes_a_waiver_still_allowed` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 386 warning(s), 790 waived
- error-findings: none (measured, zero errors)
