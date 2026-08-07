---
id: T-0808
title: 'gates: WAIVE007 dangling-waiver-ref -- unresolvable BINDING ticket ref in
  a waiver is a warning, not silence'
state: done
kind: security
origin: auditor
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- tests/test_waive_gate.py
- docs/design/registry/check-coverage.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: 'WAIVE007 gate needs a registry entry documenting it as a live,

    enforced gate rule (docs/design/registry/check-coverage.yaml,

    CHK-GATE-WAIVE007), mirroring WAIVE006''s CHK-GATE-WAIVE006 entry,

    plus the gate_rule_total bump the new rule id requires.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_waive_gate.py::TestWaive007ExemptDanglingRef::test_draft_id_is_exempt
- tests/test_waive_gate.py::TestWaive007ExemptDanglingRef::test_real_ticket_id_is_not_exempt
- tests/test_waive_gate.py::TestWaive007CommentChannel::test_ticket_attr_bound_to_unresolvable_id_fires
- tests/test_waive_gate.py::TestWaive007CommentChannel::test_binding_reason_phrase_bound_to_unresolvable_id_fires
- tests/test_waive_gate.py::TestWaive007CommentChannel::test_ticket_attr_bound_to_resolvable_id_is_silent
- tests/test_waive_gate.py::TestWaive007CommentChannel::test_ticket_attr_bound_to_draft_id_is_exempt
- tests/test_waive_gate.py::TestWaive007CommentChannel::test_no_binding_ref_at_all_is_silent
- tests/test_waive_gate.py::TestWaive007StrataChannel::test_strata_ticket_attr_bound_to_unresolvable_id_fires
- tests/test_waive_gate.py::TestWaive007StrataChannel::test_strata_ticket_attr_bound_to_draft_id_is_exempt
- tests/test_waive_gate.py::TestWaive007StrataChannel::test_strata_ticket_attr_bound_to_resolvable_id_is_silent
- tests/test_waive_gate.py::TestWaive007StrataChannel::test_no_design_dir_is_silent
- tests/test_waive_gate.py::TestWaive007Registration::test_waive007_is_a_known_gate_rule
- tests/test_waive_gate.py::TestWaive007Registration::test_waive007_gate_combines_both_channels
- tests/test_waive_gate.py::TestWaive007Registration::test_waivable_via_frob_waive_comment
- tests/test_waive_gate.py::TestWaive007RealRepo::test_zero_findings_on_real_repo
designated_repro_test: null
acceptance:
- text: GIVEN a waiver whose binding ticket reference resolves to no ticket in active
    or archive WHEN frob check runs THEN a WARNING-tier finding names the site and
    the dangling id; GIVEN a resolvable open ref THEN no finding
  evidence:
  - tests/test_waive_gate.py::TestWaive007CommentChannel::test_ticket_attr_bound_to_unresolvable_id_fires
  - tests/test_waive_gate.py::TestWaive007StrataChannel::test_strata_ticket_attr_bound_to_unresolvable_id_fires
  - tests/test_waive_gate.py::TestWaive007CommentChannel::test_ticket_attr_bound_to_resolvable_id_is_silent
threat: null
component: null
---
T-0779 reviewer finding: WAIVE006 deliberately skips unresolvable binding refs, but a dangling ref (e.g. a draft id renumbered at land -- the T-draft-8cd37914 -> T-0803 case that left four design/frob.strata waivers pointing at a dead id) is a permanent silent waiver, the same accountability shape WAIVE006 closes. Add WAIVE007 warning-tier for dangling BINDING refs (drafts in live worktrees are a legitimate transient -- consider exempting T-draft-* ids younger than N days or referenced by a live lease, document the choice).