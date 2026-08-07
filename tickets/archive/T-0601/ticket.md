---
id: T-0601
title: 'frob-exports triage: src/frob/strata, src/frob/tickets (22 symbols across
  2 packages)'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- src/frob/tickets/**
- tests/unit/test_ticket_store.py
- docs/modules/tickets.md
- tests/unit/strata/test_code_binding.py
- tests/unit/strata/test_compliance.py
- tests/unit/strata/test_audit.py
- tests/unit/strata/test_threat.py
- tests/test_registry_reconciliation_compliance.py
- tests/test_tickets_brief.py
- tests/test_ticket_journal.py
- tests/test_ticket_reconcile.py
- tests/test_tickets_leases.py
- tests/test_ticket_leases_cross_worktree.py
- tests/test_ticket_leases.py
- tests/test_tickets_mutation_evidence.py
- tests/test_gates.py
- tests/test_serve_daemon.py
- tests/test_ticket_runner_archive_force.py
- tests/test_tickets_dispatch_stale.py
- tests/test_tickets_lease_overlay.py
- tests/test_tickets.py
- tests/system/test_spawn_budget.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: 'T-0601''s per-symbol export/demote decision for src/frob/tickets/_store.py''s
    lock_path (demoted to _lock_path, no consumer outside this module and its own
    test) touches its only test module and the storage-internals doc anchor naming
    it.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: docs/modules/tickets.md
  reason: 'T-0601''s per-symbol export/demote decision for src/frob/tickets/_store.py''s
    lock_path (demoted to _lock_path, no consumer outside this module and its own
    test) touches its only test module and the storage-internals doc anchor naming
    it.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/strata/test_code_binding.py
  reason: 'Reviewer-mandated T-0601 rework (2026-07-23): re-applying the mechanical
    external-consumer test to every symbol found 23 additional demotions beyond the
    original get_file_hash-style case, each requiring updates to the sole test module
    exercising the renamed private helper.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/strata/test_compliance.py
  reason: 'Reviewer-mandated T-0601 rework (2026-07-23): re-applying the mechanical
    external-consumer test to every symbol found 23 additional demotions beyond the
    original get_file_hash-style case, each requiring updates to the sole test module
    exercising the renamed private helper.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/strata/test_audit.py
  reason: 'Reviewer-mandated T-0601 rework (2026-07-23): re-applying the mechanical
    external-consumer test to every symbol found 23 additional demotions beyond the
    original get_file_hash-style case, each requiring updates to the sole test module
    exercising the renamed private helper.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/strata/test_threat.py
  reason: 'Reviewer-mandated T-0601 rework (2026-07-23): re-applying the mechanical
    external-consumer test to every symbol found 23 additional demotions beyond the
    original get_file_hash-style case, each requiring updates to the sole test module
    exercising the renamed private helper.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_registry_reconciliation_compliance.py
  reason: 'Reviewer-mandated T-0601 rework (2026-07-23): re-applying the mechanical
    external-consumer test to every symbol found 23 additional demotions beyond the
    original get_file_hash-style case, each requiring updates to the sole test module
    exercising the renamed private helper.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_tickets_brief.py
  reason: 'Reviewer-mandated T-0601 rework (2026-07-23): re-applying the mechanical
    external-consumer test to every symbol found 23 additional demotions beyond the
    original get_file_hash-style case, each requiring updates to the sole test module
    exercising the renamed private helper.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_ticket_journal.py
  reason: 'Reviewer-mandated T-0601 rework (2026-07-23): re-applying the mechanical
    external-consumer test to every symbol found 23 additional demotions beyond the
    original get_file_hash-style case, each requiring updates to the sole test module
    exercising the renamed private helper.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_ticket_reconcile.py
  reason: 'Reviewer-mandated T-0601 rework (2026-07-23): re-applying the mechanical
    external-consumer test to every symbol found 23 additional demotions beyond the
    original get_file_hash-style case, each requiring updates to the sole test module
    exercising the renamed private helper.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_tickets_leases.py
  reason: 'Reviewer-mandated T-0601 rework (2026-07-23): re-applying the mechanical
    external-consumer test to every symbol found 23 additional demotions beyond the
    original get_file_hash-style case, each requiring updates to the sole test module
    exercising the renamed private helper.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_ticket_leases_cross_worktree.py
  reason: 'Reviewer-mandated T-0601 rework (2026-07-23): re-applying the mechanical
    external-consumer test to every symbol found 23 additional demotions beyond the
    original get_file_hash-style case, each requiring updates to the sole test module
    exercising the renamed private helper.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_ticket_leases.py
  reason: 'Reviewer-mandated T-0601 rework (2026-07-23): re-applying the mechanical
    external-consumer test to every symbol found 23 additional demotions beyond the
    original get_file_hash-style case, each requiring updates to the sole test module
    exercising the renamed private helper.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_tickets_mutation_evidence.py
  reason: 'Reviewer-mandated T-0601 rework (2026-07-23): re-applying the mechanical
    external-consumer test to every symbol found 23 additional demotions beyond the
    original get_file_hash-style case, each requiring updates to the sole test module
    exercising the renamed private helper.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_gates.py
  reason: 'Reviewer-mandated T-0601 rework (2026-07-23): re-applying the mechanical
    external-consumer test to every symbol found 23 additional demotions beyond the
    original get_file_hash-style case, each requiring updates to the sole test module
    exercising the renamed private helper.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_serve_daemon.py
  reason: 'Reviewer-mandated T-0601 rework (2026-07-23): re-applying the mechanical
    external-consumer test to every symbol found 23 additional demotions beyond the
    original get_file_hash-style case, each requiring updates to the sole test module
    exercising the renamed private helper.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_ticket_runner_archive_force.py
  reason: 'Reviewer-mandated T-0601 rework (2026-07-23): re-applying the mechanical
    external-consumer test to every symbol found 23 additional demotions beyond the
    original get_file_hash-style case, each requiring updates to the sole test module
    exercising the renamed private helper.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_tickets_dispatch_stale.py
  reason: 'Reviewer-mandated T-0601 rework (2026-07-23): re-applying the mechanical
    external-consumer test to every symbol found 23 additional demotions beyond the
    original get_file_hash-style case, each requiring updates to the sole test module
    exercising the renamed private helper.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_tickets_lease_overlay.py
  reason: 'Reviewer-mandated T-0601 rework (2026-07-23): re-applying the mechanical
    external-consumer test to every symbol found 23 additional demotions beyond the
    original get_file_hash-style case, each requiring updates to the sole test module
    exercising the renamed private helper.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_tickets.py
  reason: 'Reviewer-mandated T-0601 rework (2026-07-23): re-applying the mechanical
    external-consumer test to every symbol found 23 additional demotions beyond the
    original get_file_hash-style case, each requiring updates to the sole test module
    exercising the renamed private helper.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/system/test_spawn_budget.py
  reason: 'Reviewer-mandated T-0601 rework (2026-07-23): re-applying the mechanical
    external-consumer test to every symbol found 23 additional demotions beyond the
    original get_file_hash-style case, each requiring updates to the sole test module
    exercising the renamed private helper.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_tickets_brief.py::TestParsePlaybookSections::test_parses_numbered_headings_only
- tests/test_ticket_journal.py::TestWriteIntent::test_write_then_read_round_trips
- tests/test_ticket_leases.py::TestSweepWorktrees::test_clean_no_lease_removed
- tests/test_ticket_leases_cross_worktree.py::TestGitCommonDir::test_shared_across_linked_worktrees
- tests/test_tickets.py::TestEmptyCollectionOmission::test_dict_without_empty_collections_returned_unchanged
- tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_confirmatory_test_flagged
- tests/test_ticket_land.py::TestSpliceLedgerIdDropGuard::test_render_that_would_drop_an_id_is_refused
- tests/unit/test_ticket_store.py::TestLockPath::test_lock_path_under_frob_dir
- tests/test_worktree_guard.py::TestAgentEnvExports::test_resolves_worktree_root
- tests/unit/strata/test_compliance.py::TestRegulationCaughtByIntegrity::test_caught_by_naming_present_control_discharges
- tests/unit/strata/test_code_binding.py::TestObservedCallNames::test_bare_call_name_is_observed
- tests/unit/strata/test_compliance.py::TestCmplRegistry::test_deferred_disposition_is_refused
- tests/unit/strata/test_threat.py::TestCaughtByUnresolvedTokens::test_unknown_rule_id_is_unresolved
designated_repro_test: null
threat: null
component: null
---
frob-exports currently reports (measured 2026-07-22): src/frob/strata 5 public symbols missing from __init__.py, src/frob/tickets 17 (22 total, tickets is the largest single-package residue in this family). For each symbol, decide per-symbol: export it from the package's __init__.py, or demote it to private (leading underscore) if it should not be public API. No blanket waiver -- each symbol gets an explicit decision. Acceptance: frob-exports(src/frob/strata), frob-exports(src/frob/tickets) summary lines report 0 unresolved findings (exported, demoted, or waived-with-reason), no threshold loosened without a disclosed decision.