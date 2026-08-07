---
id: T-0753
title: 'waiver hygiene: WAIVE002 to error, WAIVE003 unnecessary-waiver detection,
  until= expiry on frob:waive'
state: done
kind: security
origin: human
created: '2026-07-22'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/graph/dsl.py
- docs/modules/gates.md
- tests/test_gates.py
- tests/test_dup_cross_lang.py
- tests/test_docblocks_gate.py
- tests/unit/test_dup_cache.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestTestGate::test_waive004_fires_on_valid_rule_zero_findings
- tests/test_gates.py::TestTestGate::test_waive004_stays_silent_on_a_genuinely_needed_waiver
- tests/test_gates.py::TestTestGate::test_waive005_expired_until_is_error
- tests/test_gates.py::TestTestGate::test_waive005_future_until_passes
- tests/test_gates.py::TestTestGate::test_waive_until_bad_date_is_malformed
- tests/test_gates.py::TestCoverageGate::test_waive002_flags_unknown_rule_id_as_ineffective
designated_repro_test: null
acceptance:
- text: GIVEN a waiver naming an unrecognized rule THEN error; GIVEN a valid-rule
    waiver whose site produces zero findings with waivers ignored THEN WAIVE003 fires;
    GIVEN an until-dated waiver past its date THEN error demanding re-review; AND
    the 3 live DEAD001 waivers are gone
  evidence:
  - tests/test_gates.py::TestCoverageGate::test_waive002_flags_unknown_rule_id_as_ineffective
threat: null
component: null
---
User question 2026-07-22 exposed the gap; measured state: WAIVE002 (waiver targets unrecognized rule id) fires WARNING-tier and 3 instances sit live right now (frob:waive DEAD001 in tests/test_dup_cross_lang.py::_isolated_dup_cache, tests/test_docblocks_gate.py::_fake_parser_factory, tests/unit/test_dup_cache.py::_close_cached_connections -- DEAD001 is not a recognized rule id). Deliver: (1) PROMOTE WAIVE002 to ERROR and fix the 3 current instances in the same change (identify what rule they meant -- likely a renamed dead-symbol rule -- and either retarget or delete); (2) NEW WAIVE003, the genuinely dangerous stale class: the waived rule is VALID but produces NO violation at that site anymore -- the fix landed, the waiver stays, silently pre-forgiving the next regression there. Detection: evaluate the rule at the site with waivers ignored; zero findings = WAIVE003. Warning-tier first with a ratchet-pool path to error (T-0569/T-0594 machinery) since some rules are context-dependent; document the known-flaky cases. (3) EXPIRY: frob:waive gains optional until="YYYY-MM-DD" reusing the frob:deprecated/debt date machinery (T-0576 precedent) -- past-date waiver = ERROR demanding re-review (re-date with reason or remove). Coordinate with T-0671 (strata bounded waivers -- one date convention, no second grammar) and note SYSWAIVE002 as the strata-side precedent already at error tier.