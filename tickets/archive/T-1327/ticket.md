---
id: T-1327
title: 'mutate: stale mutation-backup journal restore clobbers live in-progress edits'
state: done
kind: bug
origin: agent
created: '2026-07-29'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/mutate/**
- tests/test_mutate_journal.py
- docs/modules/mutate.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/mutate.md
  reason: AFFECT001 requires this doc touched alongside the _MutationJournalEntry/write_journal/record_journal_progress/restore_stale_journals
    changes; restored by section 10b's tickets.md-restore step, re-adding
  actor: logan
  at: '2026-07-31'
evidence:
- tests/test_mutate_journal.py::test_restore_refuses_when_stale_journal_no_longer_matches_on_disk_content
- tests/test_mutate_journal.py::test_restore_refuses_and_drops_a_legacy_journal_missing_current_sha256
- tests/test_mutate_journal.py::test_restore_stale_journals_is_byte_exact_crlf
- tests/test_mutate_journal.py::test_run_mutations_restores_stale_journal_from_prior_crash
designated_repro_test: null
acceptance:
- text: GIVEN a mutation journal whose recorded pre-mutation hash no longer matches
    the on-disk file WHEN restore runs THEN the file is left untouched and the stale
    entry is dropped with a WARNING naming the file
  evidence:
  - tests/test_mutate_journal.py::test_restore_refuses_when_stale_journal_no_longer_matches_on_disk_content
  - tests/test_mutate_journal.py::test_restore_refuses_and_drops_a_legacy_journal_missing_current_sha256
- text: GIVEN a crash mid-mutation with an accurate journal THEN restore still works
    as today
  evidence:
  - tests/test_mutate_journal.py::test_restore_stale_journals_is_byte_exact_crlf
  - tests/test_mutate_journal.py::test_run_mutations_restores_stale_journal_from_prior_crash
threat: null
component: null
---
Observed 2026-07-29 in worktree w26-strata-t1203 during T-1203: a frob check / mutation-testing run emitted 'WARNING: mutate: restored stale mutation-backup journal' and the restore CLOBBERED two uncommitted in-progress edits to src/frob/strata/_mutation_audit.py (the file under active development, not a mutation target of the run). The agent caught it only by noticing unexpected file content, redid the edits, and committed defensively. The T-0857 crash-safe journal exists to restore mutants after a crash -- but a STALE journal (from an earlier run, or another worktree context) must never win over newer on-disk content. Fix direction: the restore path must verify the journal entry's recorded pre-mutation content hash still matches the CURRENT file before restoring (mismatch = the file moved on legitimately -> skip restore, log, and drop the stale entry), and the journal should be invalidated at the start of any run that did not crash.