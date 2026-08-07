## Done report

Changed:
src/frob/tickets/_new_gate_rule_acceptance.py::new_gate_rule_ids
src/frob/tickets/_new_gate_rule_acceptance.py::GateRuleRegistryUnresolvable
src/frob/tickets/_new_gate_rule_acceptance.py::_gates_candidate_files
src/frob/tickets/_new_gate_rule_acceptance.py::_locate_known_rules_in_tree
src/frob/tickets/_new_gate_rule_acceptance.py::_known_rules_at_revision
docs/modules/gates.md#new-gate-rule-acceptance-policy-t-0756
design/frob.strata (tickets_ledger interface= sync for GateRuleRegistryUnresolvable)

Resolution of `_KNOWN_GATE_RULES` is now dynamic: every direct `*.py`
child of `src/frob/gates/` is a scan candidate, and whichever one
carries the literal is used, both in the current working tree and (via
`_known_rules_at_revision` trying every candidate name against
`base_ref`) across a rename boundary like the real T-1139
`gates/__init__.py` -> `gates/_waive.py` move. If the literal cannot be
resolved to exactly one candidate in the CURRENT tree, `new_gate_rule_ids`
now raises `GateRuleRegistryUnresolvable` instead of warning-and-skipping
-- the exact silent-disable failure mode T-1153 observed. An unresolvable
`base_ref` (or an ambiguous historical match) still degrades to `None`
(skip), unchanged from before -- that remains a legitimate git-side
"cannot tell" condition, distinct from the current-tree structural
failure the new exception covers.

Evidence:
tests/test_gates.py::TestNewGateRuleDynamicResolution::test_resolves_when_literal_lives_in_a_different_file
tests/test_gates.py::TestNewGateRuleDynamicResolution::test_raises_when_literal_missing_from_every_candidate
tests/test_gates.py::TestNewGateRuleDynamicResolution::test_no_gates_package_at_all_is_empty_not_a_raise
tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_detects_freshly_added_rule_id
tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_no_new_rules_is_empty
tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_unresolvable_base_ref_degrades_to_none
14 tests collected/passed via `pytest tests/test_gates.py::TestNewGateRuleDynamicResolution tests/test_tickets_new_gate_rule_acceptance.py -q` (measured: "..............  [100%]").
Acceptance [0] and [1] bound to the two new fixture tests above (resolve-dynamically and raise-loudly respectively).

Filed: none

Gates: `uv run frob check --ticket T-1155` chunked (--only gates-fast, gates-native, gates-security, lint, static) all pass 0 errors for
files this ticket touches. gates-native shows 5 pre-existing ARCH001
errors in src/frob/app/check_runner.py, src/frob/app/ticket_runner/_close_cmd.py,
src/frob/doctor.py, src/frob/tickets/_setters.py -- none touched by this
diff, already tracked by T-1162 (wave-18 fallout, filed before this
ticket started per main's own commit c6c2ee55's parent lineage) --
disclosed, not fixed here (out of this ticket's Description/Plan).
lint shows pre-existing ruff-format/ty findings in unrelated files
(doctor.py, gates/__init__.py, vet/_supplychain.py, etc.); my two touched
files (src/frob/tickets/_new_gate_rule_acceptance.py, tests/test_gates.py)
are individually ruff-check/ruff-format clean.
`uv run frob sys sync-interface --check` clean after syncing
`GateRuleRegistryUnresolvable`/`TestNewGateRuleDynamicResolution` into
design/frob.strata.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestNewGateRuleDynamicResolution::test_resolves_when_literal_lives_in_a_different_file` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestNewGateRuleDynamicResolution::test_raises_when_literal_missing_from_every_candidate` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestNewGateRuleDynamicResolution::test_no_gates_package_at_all_is_empty_not_a_raise` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_detects_freshly_added_rule_id` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_no_new_rules_is_empty` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_unresolvable_base_ref_degrades_to_none` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
