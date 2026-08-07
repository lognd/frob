---
id: T-0595
title: 'strata audit G1 (full closure): bind ENDORSE boundary predicate to an OBSERVED
  sanitizer call site in code'
state: done
kind: security
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0401
tier: ticket
sprint: null
scope:
- src/frob/strata/_threat.py
- src/frob/strata/_selfconform.py
- src/frob/strata/_code_binding.py
- src/frob/strata/_effects.py
- tests/unit/strata/test_threat.py
- tests/unit/strata/test_code_binding.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/test_threat.py
  reason: T-0595 needs regression tests in these files exercising the new observed-call-site
    join; per agent-playbook.md section 5, extending scope before recording evidence
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/unit/strata/test_code_binding.py
  reason: T-0595 needs regression tests in these files exercising the new observed-call-site
    join; per agent-playbook.md section 5, extending scope before recording evidence
  actor: logan
  at: '2026-07-22'
evidence:
- tests/unit/strata/test_threat.py::TestCodeBoundMitigationPredicate::test_no_observed_call_site_fails_closed_naming_the_boundary
- tests/unit/strata/test_threat.py::TestCodeBoundMitigationPredicate::test_observed_call_site_discharges
- tests/unit/strata/test_threat.py::TestCodeBoundMitigationPredicate::test_call_site_via_attribute_access_also_discharges
- tests/unit/strata/test_threat.py::TestCodeBoundMitigationPredicate::test_call_site_in_a_different_nodes_code_does_not_count
- tests/unit/strata/test_threat.py::TestCodeBoundMitigationPredicate::test_absent_binding_keeps_the_old_weaker_half_behavior
- tests/unit/strata/test_code_binding.py::TestObservedCallNames::test_bare_call_name_is_observed
- tests/unit/strata/test_code_binding.py::TestObservedCallNames::test_attribute_call_name_is_observed
- tests/unit/strata/test_code_binding.py::TestObservedCallNames::test_mention_with_no_call_is_not_observed
- tests/unit/strata/test_code_binding.py::TestObservedCallNames::test_call_in_a_different_nodes_files_is_not_observed
- tests/unit/strata/test_code_binding.py::TestObservedCallNames::test_unparseable_file_contributes_no_call_names
designated_repro_test: null
acceptance:
- text: GIVEN a .strata model with an ENDORSE boundary whose sanitizer does not appear
    at any observed call site in the guarded code path WHEN strata selfconform/threat
    discharge runs THEN the NoFlow/ENDORSE discharge fails closed with a finding naming
    the unbound boundary
  evidence: []
threat: tampering
component: null
---
Remaining stronger half of docs/audits/strata.md G1, deferred from T-0401 (its weaker half landed in T-0498: boundary obligations must resolve to a real in-model Claim.id). The gap: an ENDORSE boundary's predicate still discharges by model-side matching alone -- it is never joined against an OBSERVED sanitizer/validator call site in the code. Fix: bind the boundary predicate to a real call-site observation (via the code-binding layer), so a boundary with no observed sanitizer in the guarded path fails closed. NOTE: T-0401's Done report references this as T-0595 (ex-draft, id lost at land); that draft never materialized as a ledger block, so this ticket is its real replacement.