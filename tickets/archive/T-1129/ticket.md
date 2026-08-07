---
id: T-1129
title: 'gates: TICK-family check for disclosed-cut-without-ticket in done reports'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/tickets/**
- tests/test_gates.py
- docs/modules/gates.md
- docs/modules/tickets.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: T-1129 documents TICK011 in docs/modules/gates.md
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/gates.md
  reason: T-1129 documents TICK011 in docs/modules/gates.md
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/tickets.md
  reason: 'AFFECT001: tickets_gate''s own docstring changed, its affects()-closure
    doc docs/modules/tickets.md#decision-record-t-0162 must be touched'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: design/frob.strata
  reason: sys sync-interface writes interface= for the new TestTick011DisclosedCutWithoutTicket
    testsuite export
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_disclosed_follow_up_with_no_citation_fires
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_disclosure_with_a_real_citing_id_is_silent
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_not_yet_ticketed_with_no_citation_fires
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_explicit_no_ticket_needed_reason_is_silent
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_no_disclosure_phrase_is_silent
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_one_finding_per_ticket_not_per_phrase
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_numeric_count_residual_is_not_a_disclosure
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_rule_id_shaped_residue_is_not_a_disclosure
designated_repro_test: null
acceptance:
- text: GIVEN a done report whose prose discloses deferred work (left for a follow-up,
    not yet ticketed, deferred, residue, cut) WHEN frob check runs THEN a TICK-family
    finding fires unless the same report cites an open ticket id (or an explicit no-ticket-needed
    reason) within the disclosure's vicinity
  evidence:
  - tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_disclosure_with_a_real_citing_id_is_silent
- text: GIVEN the TICK011 fixture in TestTick011DisclosedCutWithoutTicket.test_disclosed_follow_up_with_no_citation_fires
    (a Done report disclosing deferred work with no ticket cited) WHEN run against
    the pre-T-1129 tickets_gate (no TICK011 check existed) THEN it FAILS to detect
    anything (0 TICK011 findings) and WHEN run against the post-T-1129 tickets_gate
    THEN it PASSES (fires exactly 1 TICK011 finding) -- proven through the production
    tickets_gate() invocation, not a pure-function unit call
  evidence:
  - tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_disclosed_follow_up_with_no_citation_fires
threat: null
component: null
---
Coordinator hand-screen made mandatory-by-tooling: wave 17 had two incidents in one wave -- T-1085 disclosed 'deliberately left for a follow-up' with no ticket (coordinator hand-filed T-1124), and T-0321's close disclosed the serve RPC gap as 'not yet ticketed as its own item' (coordinator hand-filed T-1127). TICK006 covers phantom citations; nothing covers disclosed-but-unticketed cuts. Detector should be conservative (disclosure phrases + absence of any T-#### in the same bullet/paragraph) and WARN-tier first turn-on with frob's own ledger findings fixed in the same land.