## Done report

Same as before, plus: removed the stale WIRE001 waiver on capability_ratchet_violations directly (rather than re-pointing its follow_up citation) since the wiring it disclosed as missing now exists -- closing T-1977 required re-pointing or resolving every live citation of it, and removing the now-true-again waiver was the correct fix, not a deferred one.

### Changed
```
 tickets/T-1977/done-report.md      | 21 +++++++++++++
 tickets/T-1977/ticket.md           | 63 +++++++++++++++++++++++++++++++++++++-
 tickets/T-1997/ticket.md | 25 +++++++++++++++
 3 files changed, 108 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_capability_ratchet_violation` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_does_not_fire_below_the_ratchet_ceiling` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_deleting_ratchet_lock_entry_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_shrink_then_regrow_within_ceiling_stays_silent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: DSL001@CHANGELOG.md, F401@/home/logan/projects/frob/.claude/worktrees/queue-hygiene/tests/unit/test_tickets_evidence_only_scope.py
