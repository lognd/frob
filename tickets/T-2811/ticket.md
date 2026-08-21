---
id: T-2811
title: 'Reformat batch 12/N: 13 files pending ruff-format (T-2359 child)'
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
- tests/test_tickets_body.py
- tests/test_tickets_cmd_evidence.py
- tests/test_tickets_collision.py
- tests/test_tickets_dispatch_stale.py
- tests/test_tickets_ledger_concurrency.py
- tests/test_tickets_live_tracker.py
- tests/test_tickets_migration.py
- tests/test_tickets_milestone_runs_last.py
- tests/test_tickets_milestone_sort.py
- tests/test_tickets_parent.py
- tests/test_tickets_review.py
- tests/test_tickets_scope_mutation.py
- tests/test_waive_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_tickets_body.py::TestBodyAmend::test_append_appends_text
- tests/test_tickets_cmd_evidence.py::TestIsCmdEvidence::test_shapes
- tests/test_tickets_collision.py::TestPostArchiveReissueIncident::test_new_ticket_never_reissues_an_archived_id
- tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_queued_with_live_lease_is_in_flight
- tests/test_tickets_ledger_concurrency.py::TestArchiveRaceWithConcurrentNew::test_concurrent_new_ticket_survives_a_racing_archive
- tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_empty_repo_has_no_citations
- tests/test_tickets_migration.py::TestMigrateV1ToV2::test_migrates_one_active_ticket_with_done_report
- tests/test_tickets_milestone_runs_last.py::TestRunsLastMilestoneScoping::test_unmilestoned_runs_last_keeps_global_semantics
- tests/test_tickets_milestone_sort.py::TestEffectiveMilestone::test_own_milestone_is_declared
- tests/test_tickets_parent.py::TestSetParent::test_reparents_leaf_to_epic
- tests/test_tickets_review.py::TestRecordReview::test_appends_approve_entry
- tests/test_tickets_scope_mutation.py::TestScopeLeaseConflict::test_no_collision_is_none
- tests/test_waive_gate.py::TestWaive006BindingPhraseExtraction::test_pending_phrasing_is_binding
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 304f774da62fe53f2eeed23a030160bb36235b5d
---
Batch 12 of the T-2359 ruff-format-only reformat epic. 13 files re-measured against current main via 'uv run ruff format --check .' (58 files remaining before this batch). Format-only, no semantic changes. Excludes files claimed by live in-flight tickets per fleet_status.py + .git/frob-leases/*.json re-checked fresh at pick time: T-2373's empty-scope I001 burn-down epic (historically claiming test_ticket_land.py, test_ticket_work_and_land_finish.py, test_tickets_organization.py, test_tickets_priority.py, unit/test_app_runners_batch6.py, unit/test_app_runners_t2395_contention.py), T-2806 (src/frob/gates/__init__.py, tests/unit/test_check.py), T-2805, T-2755, T-2370.