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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/**
- design/**
- docs/strata/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: condense waiver-exclusion history into T-0174 body per T-4691 C5 sweep
  actor: logan
  at: '2026-09-19'
  old_length: 767
  new_length: 2446
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
anchor: false
anchor_reason: null
land_commit: null
---
logand.app pilot: check-gate violations have frob:waive with written reasons, but sys-audit findings (SYS100-102, THREAT002/003) have no waiver channel -- external repos must either fix immediately or live with permanent red, which pushes toward gaming the model instead of honest debt. Design the analog: an in-design waive/accept declaration (surface syntax on the node/claim, e.g. an accept clause with a mandatory reason string and optional ticket ref -- reuse the assume claim machinery where it already fits rather than a parallel channel), surfaced in audit output as WAIVED with the reason, counted separately, drift-locked so reasonless or stale waivers fail. Must satisfy the same discipline as frob:waive: narrowly scoped, reason mandatory, loud in output.

<!-- narrative-moved:src/frob/strata/_audit.py:981:T-0174 -->
T-0174: this predicate sees every THREAT/LINT/PII/compliance/
CVE-fingerprint finding -- everything EXCEPT SYS100-102 (owned by
`check_self_conformance`), HOST001/HOST002 (owned by
`evaluate_host_isolation_waived`, T-0280), SYS200-203 (T-0724:
owned by `check_resource_contention`'s own `apply_waivers` call,
`_contention.py::_apply_contention_waivers`), SYS205 (T-1061/T-1157:
owned by `check_mode_conformance`'s own `apply_waivers` call,
`_mode_conformance.py::check_mode_conformance`), and REL200/REL201/
REL210/REL211 (T-0640/T-0644: owned by `check_reliability_timeouts`/
`check_reliability_health`'s shared `apply_waivers` call,
`_reliability.py::_apply_reliability_waivers`) -- each of
those owns its own waiver channel (apply_waivers' `in_scope`
docstring). Without this exclusion, a legitimate `waive "SYS20X:..."`
(or, per T-0640, `waive "REL20X:..."`) clause was reported STALE
here (this gap set never contains a matching finding) even while
the owning check correctly matched and applied the SAME waiver in
its own pass -- a real cross-family collision, not a hypothetical
one (T-0724 review round surfaced it for SYS20X on frob's own
design/frob.strata; T-0640 hit the identical collision for REL200
on the SAME file's cache-fill waivers; T-1157 hit the identical
collision for SYS205 mode-conformance waivers on the SAME file's
`tickets_ledger` resource). Excluding those rule ids here (rather
than enumerating every rule this call DOES own) keeps this
predicate correct as new gap-producing rule families are added --
a new rule id is in scope here by default, exactly like `gaps`
itself already is.