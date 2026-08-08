## Done report

Added a paragraph documenting `_warm_tree_clears_unattributed_native_noise`
(T-1847) to the "Quarantine circuit breaker (T-1693)" section of
docs/modules/tickets.md, right after the existing
`_raise_quarantine_for_red_batch` paragraph it extends. Covers the two
conditions that must both hold before a pair is dropped (UNATTRIBUTED +
rule id in _NATIVE_EXTENSION_ADJACENT_RULE_IDS), the RIGHT-NOW re-check
against unimportable_natives, and the "still broken keeps the finding"
and "everything cleared skips the raise" fallbacks.

Removed the two AFFECT001 waivers T-1847 had left on
_warm_tree_clears_unattributed_native_noise and
_raise_quarantine_for_red_batch in src/frob/app/ticket_runner/_rapid_sweep.py
now that the doc anchor they cited as a follow-up is landed.

### Changed
```
 docs/modules/tickets.md                    | 29 +++++++++++++++++++++++++++++
 src/frob/app/ticket_runner/_rapid_sweep.py | 10 ----------
 src/frob/tickets/_scope.py                 |  4 +---
 tickets/T-1832/ticket.md                   |  4 +++-
 tickets/T-1865/ticket.md                   | 16 +++++++++++++++-
 tickets/T-1878/ticket.md                   | 10 +++++++++-
 6 files changed, 57 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_warm_tree_recheck_drops_cold_worktree_native_noise` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_warm_tree_recheck_keeps_finding_when_native_still_broken` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_warm_tree_recheck_never_drops_an_attributed_finding` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 1 error(s), 1054 warning(s), 694 waived
- error-findings: PRE001@tickets/T-1865
