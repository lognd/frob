---
id: T-0632
title: 'arch: extend NormalizedCall with arg-position detail and migrate _extract_signatures/_collect_dispatch_refs
  onto the model'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0610
parent: T-0329
tier: ticket
sprint: null
scope:
- src/frob/arch/_normalized.py
- src/frob/arch/_python.py
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestPythonAdapter::test_adapt_call_args_capture_position_keyword_and_identifier
- tests/unit/test_arch.py::TestDispatchFamilySuppression::test_dispatch_family_no_abstraction_opportunity
- tests/unit/test_arch.py::TestDispatchFamilySuppression::test_accidental_same_signature_still_flagged
- tests/unit/test_arch.py::TestAbstractionOpportunityDiscriminators::test_generic_signature_unrelated_bodies_not_flagged
- tests/unit/test_arch.py::TestAbstractionOpportunityDiscriminators::test_specific_signature_genuine_family_still_flagged
designated_repro_test: null
acceptance:
- text: GIVEN the existing T-0360/T-0370 regression tests unmodified WHEN both check
    families run through the normalized model THEN all pass and no raw-tree walk remains
    in _collect_dispatch_refs (or a reasoned decision records what stays raw and why)
  evidence:
  - tests/unit/test_arch.py::TestPythonAdapter::test_adapt_call_args_capture_position_keyword_and_identifier
  - tests/unit/test_arch.py::TestDispatchFamilySuppression::test_dispatch_family_no_abstraction_opportunity
  - tests/unit/test_arch.py::TestDispatchFamilySuppression::test_accidental_same_signature_still_flagged
  - tests/unit/test_arch.py::TestAbstractionOpportunityDiscriminators::test_generic_signature_unrelated_bodies_not_flagged
  - tests/unit/test_arch.py::TestAbstractionOpportunityDiscriminators::test_specific_signature_genuine_family_still_flagged
threat: null
component: null
---
T-0610 migrated long-function/god-class/deep-nesting onto NormalizedModule but left two check families on the raw tree-sitter walk, with concrete schema gaps documented: _extract_signatures' body-fingerprint needs full raw AST for alpha-renaming, and _collect_dispatch_refs needs argument-position/dict-value detail NormalizedCall does not carry. Extend the model (arg positions on NormalizedCall; a fingerprint-friendly body projection or a documented decision to keep fingerprints raw-AST-based), then migrate both WITHOUT regressing the T-0360 dispatch-family suppression or T-0370 near-dup discriminator protections (their tests must pass unmodified). NOTE: T-0610's Done report references this as T-0632 (ex-draft, id lost at land) (prose only); this is the real ticket.