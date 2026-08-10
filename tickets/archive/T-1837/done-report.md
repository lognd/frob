## Done report

Fixed the three unowned residue findings in src/frob/registry/_staleness.py
from T-1264's land:

- E501: wrapped `_gate_rule_block`'s one long f-string return into
  separate f-string lines (line 59).
- COV001: added frob:doc edges (docs/design/registry/EXHAUSTIVENESS-GATE.md
  #reg010-gate-rule-staleness-t-0560, extended with three new
  frob:describes anchors and a paragraph on missing_gate_rule_ids) for
  missing_gate_rule_ids, sync_gate_rule_entries, sync_gate_rule_fixability.
- TEST001: bound frob:tests edges to the existing tests already covering
  missing_gate_rule_ids and sync_gate_rule_entries in
  tests/test_registry_staleness.py (no new tests needed -- coverage
  already existed, just wasn't bound).

Note: this fix physically landed on main as part of T-1787's land (same
worktree, same branch) rather than its own separate commit -- both
tickets' work was on one branch when T-1787 landed first. Verified
directly against main post-land: src/frob/registry/_staleness.py on main
carries all three frob:doc edges and the wrapped E501 fix.

### Changed
```
 tickets/T-1837/ticket.md | 7 +++++++
 1 file changed, 7 insertions(+)
```

### Evidence
- `tests/test_registry_staleness.py::TestMissingGateRuleIds::test_finds_rules_with_no_entry` (pytest node id, verified passing when recorded)
- `tests/test_registry_staleness.py::TestMissingGateRuleIds::test_fully_covered_is_empty` (pytest node id, verified passing when recorded)
- `tests/test_registry_staleness.py::TestMissingGateRuleIds::test_unreadable_file_is_empty` (pytest node id, verified passing when recorded)
- `tests/test_registry_staleness.py::TestSyncGateRuleEntries::test_appends_every_missing_rule` (pytest node id, verified passing when recorded)
- `tests/test_registry_staleness.py::TestSyncGateRuleEntries::test_already_in_sync_returns_empty_tuple` (pytest node id, verified passing when recorded)
- `tests/test_registry_staleness.py::TestSyncGateRuleEntries::test_missing_file_rejected` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 2 error(s), 639 warning(s), 739 waived
- error-findings: PRE001@tickets/T-1837, SEC110@.claude/hooks/dispatch-telemetry.py
