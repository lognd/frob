---
id: T-0174
title: waiver mechanism for sys-audit findings (SYS/THREAT rules) analogous to frob:waive
state: done
kind: feature
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- design/**
- docs/strata/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_litmus_waive.py::TestWaiveLitmus::test_matched_waiver_suppresses_the_finding
- tests/unit/strata/test_litmus_waive.py::TestWaiveLitmus::test_matched_waiver_is_surfaced_in_waived_with_reason
- tests/unit/strata/test_litmus_waive.py::TestWaiveLitmus::test_stale_waiver_reported_as_syswaive002_gap
- tests/unit/strata/test_litmus_waive.py::TestWaiveLitmus::test_stale_fails
- tests/unit/strata/test_litmus_waive.py::TestWaiveLitmus::test_sub_target_waiver_does_not_suppress_a_different_sub_target
- tests/unit/strata/test_selfconform.py::TestWaiverChannel::test_matching_waiver_moves_violation_to_waived
- tests/unit/strata/test_selfconform.py::TestWaiverChannel::test_stale
- tests/unit/strata/test_selfconform.py::TestWaiverChannel::test_sub_target_waiver_does_not_suppress_a_different_kind
- tests/unit/strata/test_waive.py::TestStaleDetail::test_names_rule_node_and_reason
- tests/unit/strata/test_waive.py::TestSplitWaiverRule::test_qualified_rule_splits_on_first_colon
- tests/unit/strata/test_waive.py::TestValidateWaiverFields::test_every_multi_instance_family_requires_sub_target
- tests/unit/strata/test_elaborate.py::TestElaborateWaivers::test_empty_reason_fails_closed
- tests/unit/strata/test_elaborate.py::TestElaborateWaivers::test_multi_instance_family_without_sub_target_fails_closed
- tests/unit/test_strata_tmlanguage.py::test_clause_keywords_covered_by_grammar
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
designated_repro_test: null
threat: null
component: null
---
logand.app pilot: check-gate violations have frob:waive with written reasons, but sys-audit findings (SYS100-102, THREAT002/003) have no waiver channel -- external repos must either fix immediately or live with permanent red, which pushes toward gaming the model instead of honest debt. Design the analog: an in-design waive/accept declaration (surface syntax on the node/claim, e.g. an accept clause with a mandatory reason string and optional ticket ref -- reuse the assume claim machinery where it already fits rather than a parallel channel), surfaced in audit output as WAIVED with the reason, counted separately, drift-locked so reasonless or stale waivers fail. Must satisfy the same discipline as frob:waive: narrowly scoped, reason mandatory, loud in output.