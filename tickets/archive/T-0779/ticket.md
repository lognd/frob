---
id: T-0779
title: 'gates: stale-waiver detection -- waive reason citing a DONE/DROPPED ticket
  is an error (WAIVE-tier)'
state: done
kind: security
origin: auditor
created: '2026-07-23'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- tests/test_waive_gate.py
- docs/design/registry/check-coverage.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: 'Adding the new WAIVE006 rule id to frob''s own reflexive check-coverage

    registry (docs/design/registry/check-coverage.yaml) is structurally

    required by the SAME change this ticket implements -- every other

    gate rule added by prior tickets (WAIVE004, WAIVE005, DEAD001, ...)

    registered itself here in the same change, and REG008/REG009 would

    otherwise immediately red main on the new frob:enforces edge. This is

    not a new task, just the one-line companion entry a new rule id always

    needs.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_pending_phrasing_is_binding
- tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_is_the_follow_on_ticket_phrasing_is_binding
- tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_bare_historical_mention_is_not_binding
- tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_built_a_real_kill_switch_narration_is_not_binding
- tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_no_ticket_mention_at_all_is_not_binding
- tests/test_waive_gate.py::TestWaive006CommentChannel::test_ticket_attr_bound_to_done_ticket_fires
- tests/test_waive_gate.py::TestWaive006CommentChannel::test_ticket_attr_bound_to_dropped_ticket_fires
- tests/test_waive_gate.py::TestWaive006CommentChannel::test_ticket_attr_bound_to_open_ticket_is_silent
- tests/test_waive_gate.py::TestWaive006CommentChannel::test_binding_reason_phrase_bound_to_done_ticket_fires
- tests/test_waive_gate.py::TestWaive006CommentChannel::test_historical_mention_of_done_ticket_is_silent
- tests/test_waive_gate.py::TestWaive006CommentChannel::test_unresolvable_ticket_id_is_silent
- tests/test_waive_gate.py::TestWaive006StrataChannel::test_strata_ticket_attr_bound_to_done_ticket_fires
- tests/test_waive_gate.py::TestWaive006StrataChannel::test_strata_binding_phrase_bound_to_dropped_ticket_fires
- tests/test_waive_gate.py::TestWaive006StrataChannel::test_strata_open_follow_on_with_historical_mention_is_silent
- tests/test_waive_gate.py::TestWaive006StrataChannel::test_no_design_dir_is_silent
- tests/test_waive_gate.py::TestWaive006Registration::test_waive006_is_a_known_gate_rule
- tests/test_waive_gate.py::TestWaive006Registration::test_waive006_gate_combines_both_channels
- tests/test_waive_gate.py::TestWaive006Registration::test_waivable_via_frob_waive_comment
- tests/test_waive_gate.py::TestWaive006RealRepo::test_zero_errors_on_real_repo
designated_repro_test: null
acceptance:
- text: GIVEN a waive directive (frob:waive or strata waive) whose reason or ticket
    attribute references a ticket that is DONE or DROPPED in the ledger/archive WHEN
    frob check runs THEN a gate error fires naming the waiver site and the closed
    ticket; GIVEN a waiver citing an open ticket THEN no finding
  evidence:
  - tests/test_waive_gate.py::TestWaive006CommentChannel::test_ticket_attr_bound_to_done_ticket_fires
  - tests/test_waive_gate.py::TestWaive006CommentChannel::test_ticket_attr_bound_to_open_ticket_is_silent
  - tests/test_waive_gate.py::TestWaive006RealRepo::test_zero_errors_on_real_repo
threat: null
component: null
---
Audit H2 gate-direction (docs/audits/frob-blindspots-2026-07-23.md): the five LINT004 kill-switch waivers cite T-0200 as the follow-on ticket to build -- but T-0200 closed long ago, and no gate re-litigates a waiver once its justifying ticket lands. A waiver justified by pending-T-XXXX must not outlive T-XXXX. Implement in the WAIVE gate family: resolve every ticket id referenced in waiver reasons/attributes against the ledger+archive; DONE/DROPPED means the waiver must be re-justified or deleted. Land AFTER T-0778 clears the five current offenders or the gate reds main immediately (sequencing note for the coordinator, not a design choice).