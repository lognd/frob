## Done report

Merged main (which already carried T-1880's unified same_worktree_lease home from _leases.py, both _scope.py and _doable.py delegating to it), reproduced 0 DUP001 findings post-merge (frob-dup: 419 duplicate groups pass, no new group), confirmed the earlier ClaimDivergence resolved organically by the merge -- no additional duplication existed to extract. Re-ran targeted tests (tests/test_ticket_leases_cross_worktree.py, tests/test_tickets_scope_mutation.py, tests/unit/test_app_runners_batch7.py: 156 passed) and frob check --ticket T-1883 (0 errors across all gate families, gate:dup pass).

### Changed
(no changed files detected)

### Evidence
- `tests/test_ticket_leases_cross_worktree.py::TestSameWorktreeLease::test_both_leased_to_same_worktree_matches` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases_cross_worktree.py::TestSameWorktreeLease::test_different_worktrees_do_not_match` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases_cross_worktree.py::TestDoableExcludesSameWorktreeLeases::test_same_worktree_colliding_leases_do_not_block_each_other` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases_cross_worktree.py::TestDoableExcludesSameWorktreeLeases::test_cross_worktree_colliding_lease_still_blocks` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 3 error(s), 1248 warning(s), 694 waived
- error-findings: invalid-argument-type@src/frob/app/ticket_runner/_lifecycle.py, invalid-argument-type@tests/test_tickets_scope_mutation.py, invalid-argument-type@tests/unit/gates/test_sys_interface_canonical_order.py
