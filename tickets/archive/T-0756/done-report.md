## Done report

Changed:
- src/frob/gates/__init__.py::sys_gate (extended: now also runs _selfaudit_violations)
- src/frob/gates/__init__.py::_selfaudit_violation
- src/frob/gates/__init__.py::_selfaudit_violations
- src/frob/gates/__init__.py::_KNOWN_GATE_RULES (added "SELFAUDIT001")
- src/frob/tickets/_new_gate_rule_acceptance.py (new module): new_gate_rule_ids, missing_acceptance_for_new_rules, _extract_known_rules, _read_gates_file_at_revision, _is_fixture_acceptance
- src/frob/tickets/_models.py::TicketError (added NewGateRuleUnaccepted)
- src/frob/tickets/__init__.py::_done_transition_guard (wired the new unconditional check, mirroring live_tracker_citations)
- design/frob.strata (node serve: added the missing SYS203:tickets_ledger waiver its 4 sibling nodes already carried)
- docs/modules/gates.md (SELFAUDIT001 table row + two new sections: "Self-audit at land" and "New-gate-rule acceptance policy")
- invariants/INV-041.md (new invariant spec for the SELFAUDIT001 lossless-fold property)
- tests/test_gates.py::TestSelfAuditGate (3 tests)
- tests/test_tickets_new_gate_rule_acceptance.py (new file, 11 tests)

Mechanism (1) SELF-AUDIT AT LAND: frob.gates.sys_gate (the production
entrypoint `frob check` already calls unconditionally whenever a design
dir exists) now folds frob's own self-conformance (SYS100-102,
frob.strata.check_self_conformance), resource-contention (SYS2xx,
check_resource_contention), and reliability (REL2xx,
check_reliability_timeouts/check_reliability_health) audit surface into
the ordinary gate pipeline under a new rule id, SELFAUDIT001 (ERROR,
registered in _KNOWN_GATE_RULES). This closes the land-preflight half of
the mandate with ZERO app/**-layer changes: frob ticket land's EXISTING
check_gates/check_gate_findings post-merge re-verification
(frob.tickets._land.land, T-0754/T-0846) already refuses a landing whose
gate-error count reddens relative to the recorded claim -- once
SELFAUDIT001 is an ordinary gate frob check reports, that machinery
covers it automatically.

REAL FINDING surfaced by turning this on: wiring SELFAUDIT001 revealed
`frob sys audit` was ALREADY red on main (one unwaived SYS203 finding on
node=serve, missing the same waiver its 4 sibling nodes -- cli/core/
fleet/gates -- already carry from T-0724). This is precisely the
"invoked-by-nothing red audit" root cause the ticket describes. Landing
SELFAUDIT001 while knowingly leaving this red would repeat the incident,
so design/frob.strata's `serve` node was scope-added (--reason-file, see
ticket scope history) and given the identical sibling waiver line.
`frob sys audit .` now exits 0 (verified: WARNING lines only, PROVED
summary for self-conformance/resource-contention/reliability).

Mechanism (2) NEW-GATE-RULE ACCEPTANCE POLICY:
frob.tickets._new_gate_rule_acceptance.new_gate_rule_ids does a
diff-aware text scan (git show base_ref vs current tree, mirroring
_live_tracker's grep-shaped-not-full-parse posture) of
src/frob/gates/__init__.py's _KNOWN_GATE_RULES frozenset literal, and
missing_acceptance_for_new_rules requires at least one BOUND acceptance
criterion whose text contains both a FAIL and a PASS marker
(case-insensitive). Wired UNCONDITIONALLY into
frob.tickets._done_transition_guard (the same DONE-transition guard both
`frob ticket close` and `frob ticket land`'s finalize-and-close step
call internally) -- no separate land-time CLI wiring needed, exactly
mirroring live_tracker_citations's existing posture. New TicketError.
NewGateRuleUnaccepted variant.

DOGFOOD (self-check, per the ticket's own mandate): T-0756's own diff
adds SELFAUDIT001 to _KNOWN_GATE_RULES. Verified directly:
new_gate_rule_ids(root, base_ref="main") == ("SELFAUDIT001",), and
missing_acceptance_for_new_rules(ticket, ("SELFAUDIT001",)) == () once
acceptance criterion [0] (pre-existing ticket text: "...no
before-fails/after-passes fixture...") was bound via
`frob ticket evidence T-0756 <fixture ids> --accepts 0`. Confirmed this
ticket cannot itself close/land without satisfying its own new policy.

Disclosed cuts (v1, documented in docs/modules/gates.md and the module
docstring, not silently dropped):
- new_gate_rule_ids is scoped to _KNOWN_GATE_RULES specifically (the one
  registry every Violation-producing gate rule must be listed in) -- a
  rule family introduced some OTHER way is a known residual gap. This
  ticket's own SELFAUDIT001 folds the previously-uncovered SYS1xx/SYS2xx/
  REL2xx families INTO _KNOWN_GATE_RULES for exactly this reason.
- missing_acceptance_for_new_rules requires ONE qualifying criterion
  covering the ticket as a whole when several rule ids land in one diff,
  not a strict 1:1 criterion-per-rule-id mapping.
- new_gate_rule_ids fails OPEN (returns None, obligation skipped) on any
  git infra failure, a deliberate asymmetry from _live_tracker's
  fail-closed posture -- explained in the function's own docstring:
  this check gates EVERY ticket close in the repo, so a transient git
  hiccup blocking all closes repo-wide is a worse failure mode than
  occasionally missing a genuinely new rule id.
- I did NOT add a fully separate `frob ticket land`-only preflight call
  site for either mechanism; both close the loop through EXISTING
  machinery (check_gates re-verification for (1), _done_transition_guard
  for (2), the latter already reached by land's own finalize-and-close
  step). This was a deliberate minimal-surface-area choice, not an
  oversight -- confirmed by tracing _land_finalize_and_close ->
  _finalize_and_close_ticket -> transition(..., DONE).

Verification (measured, all foreground, chunked --only stages):
- `uv run pytest tests/test_gates.py::TestSelfAuditGate
  tests/test_tickets_new_gate_rule_acceptance.py -q`: 14 passed
- `uv run pytest tests/test_tickets_live_tracker.py
  tests/test_tickets_mutation_evidence.py tests/test_evidence_integrity.py
  tests/test_ticket_land.py tests/test_tickets.py -q`: all passed (no
  regressions in the transition()/land() call sites this change touches)
- `uv run frob check --only lint --ticket T-0756`: PASS 0 errors 0 warnings
- `uv run frob check --only static --ticket T-0756`: 0 errors (frob-exports
  warnings are pre-existing, unrelated to this diff)
- `uv run frob check --only gates-fast --ticket T-0756 --json`: 0 errors
- `uv run frob check --only gates-native --ticket T-0756 --json`: 0 errors
- `uv run frob check --only gates-security --ticket T-0756 --json`: 0 errors
- `uv run frob sys audit .`: exit 0 (was exit 1 before design/frob.strata's
  fix -- the concrete before-fails/after-passes proof for SELFAUDIT001's
  own underlying audit surface)
- `git diff main --diff-filter=D --stat`: empty (verified before this report)

Filed: none (design/frob.strata's serve-node waiver was folded into this
ticket's own scope, not filed separately, since it is a direct
precondition for SELFAUDIT001 being landable at all -- see scope-add
reason recorded in tickets.md's scope history for T-0756).

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_selfconform_violation` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_clean_model_no_violations` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_suppressed_on_design_load_error` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_detects_freshly_added_rule_id` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_no_new_rules_is_empty` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_unresolvable_base_ref_degrades_to_none` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_no_gates_file_at_all_is_empty` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules::test_flags_when_no_fixture_criterion_bound` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules::test_clear_when_a_bound_fixture_criterion_exists` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules::test_unbound_fixture_shaped_criterion_still_flags` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules::test_empty_new_rule_ids_is_always_clear` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestTransitionRefusesOnUnacceptedNewGateRule::test_close_refused_when_new_rule_has_no_fixture_acceptance` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestTransitionRefusesOnUnacceptedNewGateRule::test_close_allowed_when_fixture_acceptance_bound` (pytest node id, verified passing when recorded)
- `tests/test_tickets_new_gate_rule_acceptance.py::TestTransitionRefusesOnUnacceptedNewGateRule::test_close_allowed_when_no_new_rule_added` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 14 passed (from 14 evidence id(s))
- gates: 0 error(s), 2258 warning(s), 219 waived
- error-findings: none (measured, zero errors)
