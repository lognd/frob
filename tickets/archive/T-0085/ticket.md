---
id: T-0085
title: strata frob sys doc + DOC002 claims audit
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0053
parent: T-0054
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- src/frob/docs/**
- src/frob/app/**
- src/frob/__main__.py
- src/frob/gates/**
- src/frob/graph/dsl.py
- docs/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_sysdoc.py::TestMergeModels::test_concat_fields
- tests/unit/strata/test_sysdoc.py::TestMergeModels::test_empty_tuple
- tests/unit/strata/test_sysdoc.py::TestRenderAuditMatrix::test_unknown_view_is_an_error
- tests/unit/strata/test_sysdoc.py::TestRenderAuditMatrix::test_empty_model_names_every_catalog_entry_unevaluated_or_absent
- tests/unit/strata/test_sysdoc.py::TestRenderAuditMatrix::test_discharged_obligation_renders_proved
- tests/unit/strata/test_sysdoc.py::TestRenderAuditMatrix::test_undischarged_obligation_renders_failing
- tests/unit/strata/test_sysdoc.py::TestRenderAuditMatrix::test_out_of_scope_entry_gets_its_own_section
- tests/unit/strata/test_sysdoc.py::TestRenderAuditMatrix::test_deterministic_rendering
- tests/unit/strata/test_sysdoc.py::TestAuditClaim::test_unknown_view_is_an_error
- tests/unit/strata/test_sysdoc.py::TestAuditClaim::test_empty_model_is_proved_no_capabilities_ever_fire
- tests/unit/strata/test_sysdoc.py::TestAuditClaim::test_undischarged_obligation_is_not_proved_and_names_it
- tests/unit/strata/test_sysdoc.py::TestAuditClaim::test_discharged_obligation_is_proved
- tests/test_gates.py::TestSysGate::test_doc003_proved_claim_passes
- tests/test_gates.py::TestSysGate::test_doc003_refutes_names_obligations
- tests/test_gates.py::TestSysGate::test_doc003_unclaimed_view_ignored
- tests/test_gates.py::TestSysGate::test_doc003_unknown_view
- tests/system/test_cli_sys_doc.py::TestSysDocCli::test_renders_matrix_for_default_view
- tests/system/test_cli_sys_doc.py::TestSysDocCli::test_unknown_view_exits_nonzero
- tests/system/test_cli_sys_doc.py::TestSysDocCli::test_no_design_dir_is_a_noop
- tests/test_gates.py::TestSysGate::test_doc003_marker_in_fenced_block_ignored
- tests/test_gates.py::TestSysGate::test_doc003_marker_in_inline_code_ignored
- tests/test_gates.py::TestSysGate::test_doc003_real_marker_with_fenced_example_extracts_once
designated_repro_test: null
threat: null
component: null
---
Generated reference (prose + mermaid topology) per module; guarantee-shaped prose in docs must cite a PROVED claim via frob:claim anchors; overclaiming documentation becomes a build failure.