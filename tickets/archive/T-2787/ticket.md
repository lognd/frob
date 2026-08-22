---
id: T-2787
title: 'Reformat batch 6/N: 13 files pending ruff-format (T-2359 child)'
state: done
kind: feature
origin: human
created: '2026-08-21'
priority: medium
parent: T-2359
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_profile_schema.py
- src/frob/gates/_rule_id_scan.py
- src/frob/gates/_testing_schema.py
- src/frob/gates/_waive.py
- src/frob/gates/_wire.py
- tests/gates/test_rule_id_scan_branches.py
- src/frob/tickets/_accept.py
- src/frob/tickets/_draft_finalize.py
- src/frob/tickets/_evidence.py
- src/frob/tickets/_leases.py
- src/frob/verify/_attribution.py
- src/frob/verify/_drain.py
- src/frob/verify/_watermark.py
evidence_scope:
- tests/unit/test_profile_table_schema.py
- tests/unit/test_testing_table_schema.py
- tests/test_waive_gate.py
- tests/unit/test_wire001_callback_keyword_argument.py
- tests/test_tickets_acceptance.py
- tests/unit/test_draft_finalize_attachments.py
- tests/test_tick013_gate.py
- tests/unit/verify/test_attribution.py
- tests/unit/verify/test_drain.py
- tests/unit/verify/test_watermark.py
- tests/test_ticket_leases.py
- tests/test_ticket_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_profile_table_schema.py::TestProfileSchemaGate::test_must_now_fire_reports_the_undeclared_key
- tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_commented_out_rule_literal_is_skipped
- tests/unit/test_testing_table_schema.py::TestTestingSchemaGate::test_testing_known_keys_reads_test_policy_model_fields
- tests/test_waive_gate.py::TestWaive009Violations::test_known_gate_rule_ids_includes_waive009
- tests/unit/test_wire001_callback_keyword_argument.py::TestWire001CallbackKeywordArgument::test_function_passed_as_keyword_argument_value_is_not_flagged
- tests/test_tickets_acceptance.py::TestUnboundAcceptance::test_empty_acceptance_list_is_never_unbound
- tests/unit/test_draft_finalize_attachments.py::TestFinalizeDraftRelocatesAttachmentRecords::test_attachment_path_follows_the_rename
- tests/test_tick013_gate.py::TestTick013EmptyScope::test_in_progress_empty_scope_fires
- tests/unit/verify/test_attribution.py::TestAttributeBatch::test_caller_break_attributes_to_the_caller_commit
- tests/unit/verify/test_drain.py::TestRunDrainAsync::test_declines_while_a_land_is_in_progress
- tests/unit/verify/test_watermark.py::TestCommitsSinceWatermark::test_counts_raw_git_commits_not_queue_entries
- tests/test_ticket_leases.py::TestRefusesTerminalState::test_refuses_done_ticket
- tests/test_ticket_evidence.py::TestSetKind::test_updates_kind_field
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 3d9e449ece3bbb58e71fab8b1aac3febaa5acdb3
---
Batch 6/N of T-2359: apply ruff-format-only reformat to 13 files.
Includes 5 files freed by T-2557 (_waive.py, _profile_schema.py,
_rule_id_scan.py, _testing_schema.py) and T-2778 (_wire.py) landing
and releasing their leases; T-2557's/T-2778's diffs were read before
reformatting to avoid re-churning fresh content. No semantic changes;
format-only diff.