---
id: T-0823
title: 'lang: LANG003 known-gap ticket refs unresolvable in adopter repos (escalates
  to ERROR outside frob itself)'
state: done
kind: bug
origin: auditor
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/lang/_support.py
- src/frob/gates/**
- tests/test_lang_conformance_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate::test_adopter_repo_with_no_frob_internal_tickets_does_not_error
- tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate::test_present_known_gap_with_open_ticket_warns
- tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate::test_present_known_gap_with_bad_ticket_ref_errors
designated_repro_test: null
acceptance:
- text: GIVEN an adopter repo whose queue carries no frob-internal ticket ids WHEN
    LANG003 evaluates a known-gap facet THEN it does not hard-error on the unresolvable
    frob-internal reference (per the chosen design), with a fixture test proving the
    adopter shape
  evidence:
  - tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate::test_adopter_repo_with_no_frob_internal_tickets_does_not_error
  - tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate::test_present_known_gap_with_open_ticket_warns
  - tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate::test_present_known_gap_with_bad_ticket_ref_errors
threat: null
component: null
---
Disclosed by T-0818's investigation (2026-07-23): LANG003's KNOWN_GAP facet
verification requires the CHECKED repo's own ticket queue to carry the
ticket id named in frob's internal _arch_status gap table (e.g. T-0329
for typescript arch). For frob itself that id resolves; for any DOWNSTREAM
adopter repo (the 8-repo rollout) the id is meaningless -- their queues
will never mirror frob-internal ids, so every known-gap facet escalates
to ERROR on adopter repos. Adjudicate the design: (a) known-gap ids
verify against frob's own shipped registry, not the checked repo's queue;
(b) gap references become adopter-neutral (URL/registry key); or (c)
document that adopters must waive. Pick one, implement, and add an
adopter-shaped fixture test (repo with no frob-internal ids).