## Done report

WIRED: frob.tickets._new_gate_rule_acceptance.unregistered_rule_ids_in_scope
(new) is the production caller for frob.gates._rule_id_scan.
find_unregistered_rule_ids -- T-1937's soundness hole (a rule id
CONSTRUCTED in code but never added to _KNOWN_GATE_RULES at all is
invisible to new_gate_rule_ids, since that function only diffs the
registry against itself, so it never even sees an id that was never
registered) is now closed at the point of highest leverage: ticket
CLOSE/LAND time, not just a test.

CALL CHAIN (production, not test-only):
frob.tickets._evidence._done_transition_diff_derived_guard (called from
_done_transition_guard, which transition(..., DONE) always runs -- the
same site T-0756's new_gate_rule_ids/missing_acceptance_for_new_rules
pair and T-0854's live_tracker_citations already run from, per this
guard's own docstring) now ALSO calls unregistered_rule_ids_in_scope(root,
ticket) after the existing NewGateRuleUnaccepted check, and refuses the
close with the new TicketError.UnregisteredGateRuleConstructed if it
returns anything non-empty. unregistered_rule_ids_in_scope locates the
CURRENT _KNOWN_GATE_RULES literal via the same _locate_known_rules_in_tree
new_gate_rule_ids already uses, calls find_unregistered_rule_ids(root,
known=<that set>, retired=RETIRED_RULE_IDS), and filters the result to
just the candidates whose first-occurrence FILE falls inside the ticket's
OWN declared scope (frob.tickets._models.scope_matches) -- deliberately
scope-limited, not repo-wide, so an unrelated pre-existing gap elsewhere
in the tree can never block a ticket that did not introduce it (repo-wide
drift stays caught by T-1937's own test suite drift-lock,
tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::
test_real_repo_registry_is_complete, unaffected by this narrowing).

PROOF IT FIRES (end-to-end through transition(), not a pure-function unit
test): tests/test_tickets_new_gate_rule_acceptance.py::
TestTransitionRefusesOnUnregisteredGateRule::
test_close_refused_when_scope_constructs_an_unregistered_rule_id builds a
real git fixture repo whose ticket scope covers a file constructing
Diagnostic(code="ZZZUNREG003") with NO matching _KNOWN_GATE_RULES entry,
calls transition(tmp_path, "T-1956", TicketState.DONE), and asserts
result.is_err with result.danger_err ==
TicketError.UnregisteredGateRuleConstructed. Its sibling
test_close_allowed_once_the_id_is_registered proves the converse: the
identical construction, but WITH the id registered in _KNOWN_GATE_RULES,
transitions cleanly. Both measured directly (pytest run below), not
asserted from reading the code.

WIRE001 confirms the production-caller gap is closed: `frob check
--ticket T-1956 --only wire` (unscoped WIRE family) reports 0 findings --
unregistered_rule_ids_in_scope now has a real caller outside its own
tests, so the T-1937 waiver's follow_up is discharged. The original
T-1937 waiver comment on find_unregistered_rule_ids itself
(src/frob/gates/_rule_id_scan.py) is now stale prose (it still correctly
describes the state as of T-1937's own land) -- left as historical
record rather than edited, since find_unregistered_rule_ids itself still
has no DIRECT caller (unregistered_rule_ids_in_scope calls it, one level
removed) and WIRE001 measured clean regardless; not touching that comment
further was a deliberate choice to avoid rewriting another ticket's
already-landed prose for a cosmetic reason.

Changed:
- src/frob/tickets/_new_gate_rule_acceptance.py::unregistered_rule_ids_in_scope (new)
- src/frob/tickets/_evidence.py::_done_transition_diff_derived_guard (wired the new check in)
- src/frob/tickets/_models.py::TicketError.UnregisteredGateRuleConstructed (new enum member)
- tests/test_tickets_new_gate_rule_acceptance.py (+8 tests: TestUnregisteredRuleIdsInScope,
  TestTransitionRefusesOnUnregisteredGateRule; _ticket()/_write_source() helpers extended)

Evidence: 5 node ids bound (see evidence list).

Gates: `frob check --ticket T-1956 --only test --only archgate --only
coverage --only wire` -- gate:COV pass (0 errors), gate:TEST pass,
gate:WIRE 0 findings (production caller confirmed). gate:ARCH's 2 errors
(src/frob/gates/_dead_symbols.py, pre-existing ARCH001 line-count) and
gate:DRIFT's 2 errors (src/frob/tickets/_land.py DRIFT002, pre-existing)
are unrelated to this ticket's files.

### Changed
```
 tickets/T-1956/ticket.md      | 29 ++++++++++++++++++++++++++++-
 tickets/T-1958/done-report.md | 43 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-1958/ticket.md      |  4 +++-
 3 files changed, 74 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_tickets_new_gate_rule_acceptance.py::TestUnregisteredRuleIdsInScope::test_empty_when_nothing_unregistered_in_scope` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestUnregisteredRuleIdsInScope::test_reports_an_unregistered_id_whose_file_is_in_scope` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestUnregisteredRuleIdsInScope::test_excludes_an_unregistered_id_outside_scope` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestTransitionRefusesOnUnregisteredGateRule::test_close_refused_when_scope_constructs_an_unregistered_rule_id` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestTransitionRefusesOnUnregisteredGateRule::test_close_allowed_once_the_id_is_registered` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 4 error(s), 1079 warning(s), 706 waived
- error-findings: ARCH001@src/frob/gates/_dead_symbols.py, DOC002@src/frob/tickets/_land.py, DRIFT002@src/frob/tickets/_land.py, DUP001@tests/test_tickets_new_gate_rule_acceptance.py
