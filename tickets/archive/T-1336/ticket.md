---
id: T-1336
title: RENDER001 x4 + ARCH001 + COV007/COV001 residue in src/frob/refactor
state: done
kind: bug
origin: agent
created: '2026-07-31'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/refactor/**
- design/frob.strata
- docs/modules/refactor.md
- docs/commands/refactor.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/commands/refactor.md
  reason: 'AFFECT001: run_refactor_command''s affects()-closure doc is docs/commands/refactor.md#cli/#public-api-reference;
    touch it in the same change per playbook sec 6'
  actor: logan
  at: '2026-07-31'
evidence:
- tests/test_refactor.py::TestCli::test_add_refactor_parser_registers_move_and_rename
- tests/test_refactor.py::TestCli::test_run_refactor_command_reports_refusal_exit_code
- tests/test_refactor.py::TestScanReferences::test_finds_from_import_call_site
- tests/test_refactor.py::TestScanReferences::test_auto_alias_on_call_site_name_collision
- tests/test_refactor.py::TestApplyPlan::test_overlapping_ops_refuse_before_write
- tests/test_refactor.py::TestApplyPlan::test_apply_then_rollback_restores_tree
designated_repro_test: null
acceptance:
- text: given frob check, when gate:RENDER runs, then src/frob/refactor/_cli.py raises
    0 RENDER001 findings
  evidence:
  - tests/test_refactor.py::TestCli::test_add_refactor_parser_registers_move_and_rename
  - tests/test_refactor.py::TestCli::test_run_refactor_command_reports_refusal_exit_code
- text: given frob check, when gate:ARCH runs, then _handle_from_import is under the
    60-line threshold
  evidence:
  - tests/test_refactor.py::TestScanReferences::test_finds_from_import_call_site
  - tests/test_refactor.py::TestScanReferences::test_auto_alias_on_call_site_name_collision
- text: given frob check, when gate:COV runs, then the frob.refactor COV001 doc edge
    and the _find_overlapping_ops COV007 are resolved
  evidence:
  - tests/test_refactor.py::TestApplyPlan::test_overlapping_ops_refuse_before_write
  - tests/test_refactor.py::TestApplyPlan::test_apply_then_rollback_restores_tree
threat: null
component: refactor
---
Error-level gate residue confined to the refactor package: 4 RENDER001 bare prints in _cli.py (route through frob.render Renderer), ARCH001 _handle_from_import 63/60 lines in _scan.py, COV007 frob:doc on private _apply.py::_find_overlapping_ops, COV001 design/frob.strata:2125 frob.refactor public with no frob:doc edge.