## Done report

Added `_warm_tree_clears_unattributed_native_noise` and the
`_NATIVE_EXTENSION_ADJACENT_RULE_IDS` allowlist to
src/frob/app/ticket_runner/_rapid_sweep.py. `_raise_quarantine_for_red_batch`
now filters `pairs` through this helper before naming the batch: a pair
that is UNATTRIBUTED and rule-shaped like cold-worktree native-extension
noise (currently just `unresolved-import`) is re-checked right now against
`frob.strata._native_staleness.unimportable_natives(root)`; if every
declared native imports cleanly at that moment the pair is dropped from
what raises quarantine (it is still filed as a regression ticket by
`_file_regression_ticket`, unchanged). A pair whose native is still
unimportable, or that is already attributed, is never dropped -- the raise
proceeds exactly as before T-1847 for those.

Three new tests cover: (1) the noise-drop path when natives import cleanly
now, (2) the finding is kept when a native is still broken, (3) an
attributed finding is never dropped by this check even when the rule id
matches and natives read as warm.

docs/modules/tickets.md's own paragraph for this could not be added in this
ticket -- the file is leased in-scope by the concurrently in-progress
T-1686 (ScopeLeaseConflict on `frob ticket scope T-1847 --add
docs/modules/tickets.md`). Waived AFFECT001 on both changed symbols with a
reason naming this, and filed T-1865 (docs kind, scope
docs/modules/tickets.md) as the follow-up to add the paragraph once
T-1686's lease releases.

### Changed
```
 tickets/T-1847/ticket.md           | 19 ++++++++++++++++++-
 tickets/T-1865/ticket.md | 30 ++++++++++++++++++++++++++++++
 2 files changed, 48 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_warm_tree_recheck_drops_cold_worktree_native_noise` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_warm_tree_recheck_keeps_finding_when_native_still_broken` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_warm_tree_recheck_never_drops_an_attributed_finding` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 2 error(s), 660 warning(s), 744 waived
- error-findings: DOCENUM001@docs/modules/gates.md, E501@/home/logan/projects/frob/.claude/worktrees/runner-wiring/src/frob/gates/_policy_weakening_gate.py
