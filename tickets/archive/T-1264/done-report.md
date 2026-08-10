## Done report

Built the generated-verified fixability registry field per docs/design/
check-fix-engine.md's "Fixability registry field" section.

New src/frob/gates/_fixability_scan.py: generated_fixability(known_rule_ids)
maps every id to auto (TIER_A_HANDLERS)/verified (TIER_B_HANDLERS)/assisted
(TIER_C_EMITTERS)/manual (none of the three), raising FixabilityConflict if
a rule id appears in more than one table. _KNOWN_RULE_FIXABILITY (checked-in
generated literal, non-manual entries only) added to frob.gates.__init__,
with tests/test_gates.py::TestRuleFixability re-verifying it against a fresh
scan every run (drift-lock, same shape as TestKnownGateRuleIds).

src/frob/registry/_staleness.py: sync_gate_rule_entries now writes a
fixability: field on every newly-appended CHK-GATE-<rule> entry, and a new
sync_gate_rule_fixability backfills the field onto existing entries that
predate T-1264 -- called automatically from sync_gate_rule_entries's own
"already in sync" path so the one blessed sync entrypoint keeps both halves
current. Applied once to docs/design/registry/check-coverage.yaml's 291
existing entries.

Caught and fixed a real bug during implementation: the first backfill
attempt inserted the fixability: line with the wrong indent (6 spaces
instead of the entry fields' fixed 4-space indent), corrupting the YAML
(caught by REG005 in --ticket check, not by the unit test as first written
-- the test now also parses the result with yaml.safe_load and asserts on
the parsed structure, not just a substring).

Filed: none -- acceptance criterion 3 (registry sync) implemented in scope,
no residue.

Gates: frob check --ticket T-1264 clean across gates-fast/gates-native/
gates-security (0 errors each); frob check --land-parity clean (0 unscoped
errors). SELFAUDIT001/SYS104 interface drift fixed via frob sys
sync-interface (design/frob.strata gates/registry_model nodes). WIRE001
resolved by wiring sync_gate_rule_fixability as a real caller from
sync_gate_rule_entries rather than a waiver.

### Changed
```
 tickets/T-1264/ticket.md | 44 +++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 43 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_gates.py::TestRuleFixability::test_every_known_rule_id_maps_to_exactly_one_tier` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRuleFixability::test_conflicting_registration_raises_fixabilityconflict` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRuleFixability::test_checked_in_literal_matches_a_fresh_scan` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRuleFixability::test_sync_gate_rule_fixability_backfills_missing_field` (pytest node id, verified passing when recorded)
- `tests/test_registry_staleness.py::TestSyncGateRuleEntries::test_already_in_sync_returns_empty_tuple` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 1340 warning(s), 738 waived
- error-findings: none (measured, zero errors)
