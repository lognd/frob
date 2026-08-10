## Done report

Added a paragraph to the "Cross-worktree lease side-channel (T-0473)"
section of docs/modules/tickets.md documenting `_scope_add_live_lease_
conflict` (T-1868): the confirmed incident (T-1863/T-1822 both holding
`design/frob.strata` 36s apart, neither refused), the fix (checking
`read_all_leases` in addition to the local queue, mirroring `frob ticket
start`'s own foreign-lease refusal), and that T-1356's same-worktree
exemption and T-0561's new-file carve-out both still apply.

Swapped the interim `frob:todo T-1878` pointer on
_scope_add_live_lease_conflict (src/frob/tickets/_scope.py) for a real
`frob:doc` anchor at the section above, now that it exists.

### Changed
```
 docs/modules/tickets.md  | 20 ++++++++++++++++++++
 tickets/T-1878/ticket.md |  2 ++
 2 files changed, 22 insertions(+)
```

### Evidence
- `tests/test_ticket_leases_cross_worktree.py::TestScopeAddRefusesLiveCrossWorktreeLease::test_scope_add_refused_by_unmerged_sibling_worktrees_live_lease` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 1 error(s), 1039 warning(s), 694 waived
- error-findings: PRE001@tickets/T-1878
