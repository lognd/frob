---
id: T-1428
title: 'WIRE001: refuse a ticket that adds code nothing outside its own tests can
  reach'
state: done
kind: feature
origin: human
created: '2026-08-02'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_dead_symbols.py
- tests/test_gates.py
- docs/modules/gates.md
- src/frob/gates/__init__.py
- src/frob/gates/_waive.py
- src/frob/check/__init__.py
- src/frob/tickets/_accept.py
- tests/unit/test_ticket_close_bug002_t1427.py
- docs/design/registry/check-coverage.yaml
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'WIRE001 is a new gate rule; per this repo''s own established pattern (T-0422/DEAD001),
    a gate function must be registered in src/frob/gates/__init__.py''s job dispatch
    table and its rule id added to _KNOWN_GATE_RULES (src/frob/gates/_waive.py) or
    it is dead code that nothing reaches -- exactly the defect class this ticket exists
    to detect. Widening scope to these two files is necessary to avoid landing an
    inert gate.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'WIRE001 is a new gate rule; per this repo''s own established pattern (T-0422/DEAD001),
    a gate function must be registered in src/frob/gates/__init__.py''s job dispatch
    table and its rule id added to _KNOWN_GATE_RULES (src/frob/gates/_waive.py) or
    it is dead code that nothing reaches -- exactly the defect class this ticket exists
    to detect. Widening scope to these two files is necessary to avoid landing an
    inert gate.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/check/__init__.py
  reason: 'src/frob/check/__init__.py''s gates-security stage group must list "wire"
    alongside dead_symbols/protocol_summary or --only gates-security silently never
    runs it (T-1010''s own DOC006 --only-group omission precedent) -- necessary wiring
    for this ticket''s own gate, not scope creep.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/tickets/_accept.py
  reason: 'frob ticket land''s pre-land Tier-A auto-fix pass (frob fmt directive canonicalization)
    reflows the frob:waive INV006/OPAQUE001 comment line-wraps in these two pre-existing
    files unrelated to WIRE001''s own change; the reflow is purely cosmetic (identical
    reason text, different wrap points) but the WAIVE004 stale-waiver detector sees
    the old exact-text waiver as deleted, refusing land as an out-of-scope deletion.
    Scoping the two files in so land''s own deterministic fix can land is safer than
    fighting the auto-fix or hand-reverting a mechanical pass that will just re-fire
    on the next land attempt.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/unit/test_ticket_close_bug002_t1427.py
  reason: 'frob ticket land''s pre-land Tier-A auto-fix pass (frob fmt directive canonicalization)
    reflows the frob:waive INV006/OPAQUE001 comment line-wraps in these two pre-existing
    files unrelated to WIRE001''s own change; the reflow is purely cosmetic (identical
    reason text, different wrap points) but the WAIVE004 stale-waiver detector sees
    the old exact-text waiver as deleted, refusing land as an out-of-scope deletion.
    Scoping the two files in so land''s own deterministic fix can land is safer than
    fighting the auto-fix or hand-reverting a mechanical pass that will just re-fire
    on the next land attempt.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: 'tests/test_registry_exhaustiveness.py requires a CHK-GATE-<RULE> registry
    entry for every live enforced gate rule id; WIRE001/WIRE002 need matching entries
    in docs/design/registry/check-coverage.yaml or they fail that exhaustiveness check
    the same way a sibling ticket''s BUG002 omission is currently failing it.

    '
  actor: logan
  at: '2026-08-02'
- op: add
  glob: design/frob.strata
  reason: 'frob sys sync-interface (absorbed automatically by frob ticket land, playbook
    item 5) added design/frob.strata entries for the new wire_gate interface and TestWireGate
    testsuite symbol this ticket introduces -- generated state that follows directly
    from WIRE001/WIRE002''s own addition, not a separate concern.

    '
  actor: logan
  at: '2026-08-02'
evidence:
- tests/test_gates.py::TestWireGate::test_new_public_function_with_no_caller_is_flagged
- tests/test_gates.py::TestWireGate::test_new_function_called_from_non_test_code_is_not_flagged
- tests/test_gates.py::TestWireGate::test_new_rule_id_missing_from_known_gate_rules_is_flagged
- tests/test_gates.py::TestWireGate::test_new_rule_id_present_in_known_gate_rules_is_not_flagged
- tests/test_gates.py::TestWireGate::test_new_cli_dest_missing_from_config_external_is_flagged
- tests/test_gates.py::TestWireGate::test_new_cli_dest_present_in_config_external_is_not_flagged
- tests/test_gates.py::TestWireGate::test_wire002_fires_when_follow_up_ticket_missing
- tests/test_gates.py::TestWireGate::test_wire002_fires_when_follow_up_ticket_is_closed
- tests/test_gates.py::TestWireGate::test_wire002_clean_when_follow_up_ticket_is_open
designated_repro_test: null
acceptance:
- text: GIVEN a ticket diff adding a function, parameter, or registry entry that no
    non-test code reaches WHEN the gate runs THEN it is refused, reconstructed as
    a fixture from a real prior instance
  evidence:
  - tests/test_gates.py::TestWireGate::test_new_public_function_with_no_caller_is_flagged
  - tests/test_gates.py::TestWireGate::test_new_function_called_from_non_test_code_is_not_flagged
  - tests/test_gates.py::TestWireGate::test_new_rule_id_missing_from_known_gate_rules_is_flagged
  - tests/test_gates.py::TestWireGate::test_new_rule_id_present_in_known_gate_rules_is_not_flagged
  - tests/test_gates.py::TestWireGate::test_new_cli_dest_missing_from_config_external_is_flagged
  - tests/test_gates.py::TestWireGate::test_new_cli_dest_present_in_config_external_is_not_flagged
  - tests/test_gates.py::TestWireGate::test_wire002_fires_when_follow_up_ticket_missing
  - tests/test_gates.py::TestWireGate::test_wire002_fires_when_follow_up_ticket_is_closed
  - tests/test_gates.py::TestWireGate::test_wire002_clean_when_follow_up_ticket_is_open
- text: GIVEN a properly wired change WHEN the gate runs THEN it is permitted, so
    the rule is not simply refusing every addition
  evidence:
  - tests/test_gates.py::TestWireGate::test_new_public_function_with_no_caller_is_flagged
  - tests/test_gates.py::TestWireGate::test_new_function_called_from_non_test_code_is_not_flagged
  - tests/test_gates.py::TestWireGate::test_new_rule_id_missing_from_known_gate_rules_is_flagged
  - tests/test_gates.py::TestWireGate::test_new_rule_id_present_in_known_gate_rules_is_not_flagged
  - tests/test_gates.py::TestWireGate::test_new_cli_dest_missing_from_config_external_is_flagged
  - tests/test_gates.py::TestWireGate::test_new_cli_dest_present_in_config_external_is_not_flagged
  - tests/test_gates.py::TestWireGate::test_wire002_fires_when_follow_up_ticket_missing
  - tests/test_gates.py::TestWireGate::test_wire002_fires_when_follow_up_ticket_is_closed
  - tests/test_gates.py::TestWireGate::test_wire002_clean_when_follow_up_ticket_is_open
- text: GIVEN a deliberate two-phase landing WHEN the addition names the follow-up
    ticket expected to wire it THEN it is permitted and that obligation is recorded
    rather than forgotten
  evidence:
  - tests/test_gates.py::TestWireGate::test_new_public_function_with_no_caller_is_flagged
  - tests/test_gates.py::TestWireGate::test_new_function_called_from_non_test_code_is_not_flagged
  - tests/test_gates.py::TestWireGate::test_new_rule_id_missing_from_known_gate_rules_is_flagged
  - tests/test_gates.py::TestWireGate::test_new_rule_id_present_in_known_gate_rules_is_not_flagged
  - tests/test_gates.py::TestWireGate::test_new_cli_dest_missing_from_config_external_is_flagged
  - tests/test_gates.py::TestWireGate::test_new_cli_dest_present_in_config_external_is_not_flagged
  - tests/test_gates.py::TestWireGate::test_wire002_fires_when_follow_up_ticket_missing
  - tests/test_gates.py::TestWireGate::test_wire002_fires_when_follow_up_ticket_is_closed
  - tests/test_gates.py::TestWireGate::test_wire002_clean_when_follow_up_ticket_is_open
- text: GIVEN a new CLI flag whose dest never appears in AppConfig from_external copy
    lists WHEN the gate runs THEN it is caught, since that wiring is a string in a
    list and invisible to the call graph
  evidence:
  - tests/test_gates.py::TestWireGate::test_new_public_function_with_no_caller_is_flagged
  - tests/test_gates.py::TestWireGate::test_new_function_called_from_non_test_code_is_not_flagged
  - tests/test_gates.py::TestWireGate::test_new_rule_id_missing_from_known_gate_rules_is_flagged
  - tests/test_gates.py::TestWireGate::test_new_rule_id_present_in_known_gate_rules_is_not_flagged
  - tests/test_gates.py::TestWireGate::test_new_cli_dest_missing_from_config_external_is_flagged
  - tests/test_gates.py::TestWireGate::test_new_cli_dest_present_in_config_external_is_not_flagged
  - tests/test_gates.py::TestWireGate::test_wire002_fires_when_follow_up_ticket_missing
  - tests/test_gates.py::TestWireGate::test_wire002_fires_when_follow_up_ticket_is_closed
  - tests/test_gates.py::TestWireGate::test_wire002_clean_when_follow_up_ticket_is_open
threat: null
component: null
---
New code that nothing reaches is the single most repeated defect in this repo's recent history. Five clean instances landed in one session, every one of them disclosed honestly, every one with passing tests, and every one leaving the feature or guard completely inert on main.

  T-1384  own_obligations_clean added to frob.tickets._evidence. Nothing computed it. Follow-up T-1387.
  T-1399  gate_claims_verified added to the same module. Nothing computed it. Follow-up T-1410.
  T-1391  only_paths added to FMT001's fix handler. Nothing passed it. Follow-up still open.
  T-1421  bug_repro_violations, the BUG002 gate itself. No caller. Follow-up T-1427.
  T-1422  CLI flags --amend/--remove parsed by argparse and silently dropped by AppConfig.from_external's hand-maintained field lists, so the command reported it needed the very flags just passed. Fixed in commit 8ff20668.

Two more from the same session are adjacent rather than identical, and worth counting as the same family of "landed, looked done, did nothing": T-1239 fixed one exception class in the cache recovery path and left a neighbouring one still destroying shared caches (T-1416); T-1401 corrected the coverage ratchet clamp but its write does not survive to git (T-1419).

WHY IT KEEPS HAPPENING, and why it is not a discipline problem. A ticket declares a scope. The new code and its call site almost always live in different modules -- a guard in frob.tickets, its computation in frob.app.ticket_runner; a gate in frob.gates, its registration in that package's __init__; a CLI flag in _cli_parsers, its field copy in app/config. Working strictly within a declared scope therefore produces an inert change BY DEFAULT, and the agent then correctly files a follow-up for the wiring. Every one of those agents did the right thing under the rules they were given. The rules make the trap.

Nothing currently detects it. The unit tests pass because they exercise the new function directly. TEST016 passes because the diff IS mutation-detectable by its own evidence -- it cannot see an absent caller, since there is no mutant to survive. The gates are green, the ticket closes, the hazard is untouched. This is the same class as T-1399's finding one level up: acceptance verifies THE CHANGE, not THE EFFECT.

WHAT TO BUILD. A rule -- WIRE001 or similar -- that fires when a ticket's own diff introduces a symbol, parameter, or registry entry that nothing outside the diff's own tests can reach. DEAD001 already does the neighbouring analysis for private symbols with no call-graph caller; this is the same question asked about newly-added code, including code that is public and therefore exempt from DEAD001 today.

Cases it must catch, drawn from the five above: a new function with no non-test caller; a new keyword-only parameter that no call site passes; a new gate rule id absent from _KNOWN_GATE_RULES; a new CLI flag whose dest never appears in AppConfig.from_external's copy lists. That last one is worth special attention because it is invisible to the call graph entirely -- the wiring is a string in a list, not a call -- and it has now bitten twice (config.py's own comment already warns that fields get "silently dropped before AppConfig(**d)").

Cases it must NOT catch, or it will be waived into uselessness: a genuine public API addition intended for downstream consumers; a parameter with a default that existing callers are meant to keep using; an interface implemented for a protocol that is dispatched dynamically. The escape hatch should require naming WHO is expected to call it and by when -- a frob:until-style binding to the follow-up ticket, so an intentional two-phase landing is recorded rather than forgotten. That converts today's honest-but-invisible disclosure into an enforced obligation.

ACCEPTANCE MUST BE SELF-DEMONSTRATING. Reconstruct T-1384 or T-1421 as a fixture: a guard parameter added with no caller, unit-tested, passing every existing gate, must be REFUSED by this rule. And a properly wired change must be permitted. Without both directions this becomes another guard that ships inert -- which would be a genuinely absurd outcome for this particular ticket.