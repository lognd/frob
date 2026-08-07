---
id: T-0857
title: 'mutate: crashed harness leaves mutants on disk -- journal originals and detect/restore
  leftovers'
state: done
kind: bug
origin: agent
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/mutate/**
- src/frob/doctor.py
- docs/modules/mutate.md
- docs/guides/install.md
- tests/test_mutate_journal.py
- tests/system/test_cli_doctor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/mutate.md
  reason: journal design/docs + crash-simulation evidence test + doctor test coverage
    per ticket instructions
  actor: logan
  at: '2026-07-23'
- op: add
  glob: docs/guides/install.md
  reason: journal design/docs + crash-simulation evidence test + doctor test coverage
    per ticket instructions
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_mutate_journal.py
  reason: journal design/docs + crash-simulation evidence test + doctor test coverage
    per ticket instructions
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/system/test_cli_doctor.py
  reason: journal design/docs + crash-simulation evidence test + doctor test coverage
    per ticket instructions
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_mutate_journal.py::test_write_journal_is_idempotent_for_same_content
- tests/test_mutate_journal.py::test_write_journal_refuses_on_content_collision
- tests/test_mutate_journal.py::test_remove_journal_after_restore
- tests/test_mutate_journal.py::test_list_stale_journals_reports_without_restoring
- tests/test_mutate_journal.py::test_restore_stale_journals_is_byte_exact_crlf
- tests/test_mutate_journal.py::test_restore_stale_journals_after_simulated_crash
- tests/test_mutate_journal.py::test_restore_and_list_skip_a_journal_owned_by_a_live_pid
- tests/test_mutate_journal.py::test_run_mutations_restores_stale_journal_from_prior_crash
- tests/test_mutate_journal.py::test_run_mutations_journals_and_cleans_up_on_success
- tests/test_mutate_journal.py::test_run_mutations_journal_collision_aborts_with_journal_collision_error
- tests/system/test_cli_doctor.py::TestDoctorMutateJournal::test_run_diagnosis_healthy_with_no_mutate_journals
- tests/system/test_cli_doctor.py::TestDoctorMutateJournal::test_run_diagnosis_unhealthy_with_stale_mutate_journal
- tests/system/test_cli_doctor.py::TestDoctorMutateJournal::test_run_diagnosis_ignores_journal_owned_by_live_pid
- tests/test_mutate_journal.py::test_recycled_pid_with_mismatched_starttime_is_treated_stale
- tests/test_mutate_journal.py::test_write_journal_cleans_up_temp_file_on_replace_failure
designated_repro_test: null
threat: null
component: null
---
Seen in the T-0755 fork-bomb recovery: killing mutation-harness processes mid-run left real source files in mutant form (ast.unparse output: comments/waivers stripped, quotes flipped) with the true content existing nowhere on disk -- the coordinator had to reconstruct from git plus re-apply uncommitted edits by hand. run_mutations restores on normal exits only. Fix: journal each file's pre-mutation bytes to .frob/mutate-backup/ before the first write and clean up on success; on startup, detect a stale journal and restore (or instruct); teach frob doctor to flag a present mutate-backup journal as needs-restore state. Also consider a guard that any evidence test importing frob.mutate against the real repo must honor MUTATION_RUN_ENV (the recursion class).