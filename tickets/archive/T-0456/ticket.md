---
id: T-0456
title: 'crash/interrupt recovery: reconcile orphaned in-progress tickets, stale leases,
  dirty/abandoned worktrees, and partial multi-step ops (land) after power/network
  loss -- intent-journal + atomic ledger writes + frob ticket reconcile'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/
- src/frob/app/ticket_runner.py
- src/frob/__main__.py
- docs/
- tests/unit/test_ticket_store.py
- tests/test_ticket_journal.py
- tests/test_ticket_land.py
- tests/test_ticket_reconcile.py
- src/frob/app/ack_runner.py
- src/frob/release/__init__.py
- tests/test_ack_worktree_lease.py
- tests/test_release_worktree_lease.py
- tickets-archive.md
- pyproject.toml
- .frob-release.json
- CHANGELOG.md
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: T-0456 tickets work maps to tests/unit/test_ticket_store.py
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_ticket_journal.py
  reason: T-0456 wires the intent journal into land()/reconcile(), touching their
    existing test files, plus a new tests/test_ticket_journal.py
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_ticket_land.py
  reason: T-0456 wires the intent journal into land()/reconcile(), touching their
    existing test files, plus a new tests/test_ticket_journal.py
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_ticket_reconcile.py
  reason: T-0456 wires the intent journal into land()/reconcile(), touching their
    existing test files, plus a new tests/test_ticket_journal.py
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/app/ack_runner.py
  reason: 'sequential single-worktree dispatch: T-0507''s committed files still show
    in the diff-vs-main SCOPE001 check (T-0431 precedent); pyproject/.frob-release.json/CHANGELOG.md/uv.lock
    for T-0456''s own REL001 version bump (new public frob.tickets._journal API)'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/release/__init__.py
  reason: 'sequential single-worktree dispatch: T-0507''s committed files still show
    in the diff-vs-main SCOPE001 check (T-0431 precedent); pyproject/.frob-release.json/CHANGELOG.md/uv.lock
    for T-0456''s own REL001 version bump (new public frob.tickets._journal API)'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_ack_worktree_lease.py
  reason: 'sequential single-worktree dispatch: T-0507''s committed files still show
    in the diff-vs-main SCOPE001 check (T-0431 precedent); pyproject/.frob-release.json/CHANGELOG.md/uv.lock
    for T-0456''s own REL001 version bump (new public frob.tickets._journal API)'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_release_worktree_lease.py
  reason: 'sequential single-worktree dispatch: T-0507''s committed files still show
    in the diff-vs-main SCOPE001 check (T-0431 precedent); pyproject/.frob-release.json/CHANGELOG.md/uv.lock
    for T-0456''s own REL001 version bump (new public frob.tickets._journal API)'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tickets-archive.md
  reason: 'sequential single-worktree dispatch: T-0507''s committed files still show
    in the diff-vs-main SCOPE001 check (T-0431 precedent); pyproject/.frob-release.json/CHANGELOG.md/uv.lock
    for T-0456''s own REL001 version bump (new public frob.tickets._journal API)'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: 'sequential single-worktree dispatch: T-0507''s committed files still show
    in the diff-vs-main SCOPE001 check (T-0431 precedent); pyproject/.frob-release.json/CHANGELOG.md/uv.lock
    for T-0456''s own REL001 version bump (new public frob.tickets._journal API)'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: 'sequential single-worktree dispatch: T-0507''s committed files still show
    in the diff-vs-main SCOPE001 check (T-0431 precedent); pyproject/.frob-release.json/CHANGELOG.md/uv.lock
    for T-0456''s own REL001 version bump (new public frob.tickets._journal API)'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: 'sequential single-worktree dispatch: T-0507''s committed files still show
    in the diff-vs-main SCOPE001 check (T-0431 precedent); pyproject/.frob-release.json/CHANGELOG.md/uv.lock
    for T-0456''s own REL001 version bump (new public frob.tickets._journal API)'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: 'sequential single-worktree dispatch: T-0507''s committed files still show
    in the diff-vs-main SCOPE001 check (T-0431 precedent); pyproject/.frob-release.json/CHANGELOG.md/uv.lock
    for T-0456''s own REL001 version bump (new public frob.tickets._journal API)'
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/test_ticket_store.py::TestAtomicWrite::test_fsyncs_file_before_replace
- tests/unit/test_ticket_store.py::TestAtomicWrite::test_fsync_failure_is_write_failed_not_a_partial_file
- tests/test_ticket_journal.py::TestWriteIntent::test_write_then_read_round_trips
- tests/test_ticket_journal.py::TestWriteIntent::test_write_failure_returns_err
- tests/test_ticket_journal.py::TestClearIntent::test_clear_removes_the_file
- tests/test_ticket_journal.py::TestClearIntent::test_clear_missing_file_is_a_no_op
- tests/test_ticket_journal.py::TestReadAllIntents::test_reads_every_recorded_intent
- tests/test_ticket_journal.py::TestReadAllIntents::test_no_journal_dir_returns_empty
- tests/test_ticket_journal.py::TestReadAllIntents::test_malformed_record_is_skipped_not_fatal
- tests/test_ticket_journal.py::TestLandIntent::test_model_round_trips_via_json
- tests/test_ticket_reconcile.py::TestReconcileOrphanedLandIntent::test_dry_run_reports_but_does_not_clear
- tests/test_ticket_reconcile.py::TestReconcileOrphanedLandIntent::test_apply_clears_the_orphaned_intent
- tests/test_ticket_reconcile.py::TestReconcileOrphanedLandIntent::test_no_intents_reports_empty
designated_repro_test: null
threat: null
component: null
---
User request 2026-07-20: what is the recovery path when power/internet dies
mid-operation and the system is left in an intermediate state? Today an agent
that dies leaves its ticket stuck in-progress (holding a T-0453 lease), a
dirty/abandoned worktree, half-recorded evidence, and no Done report -- the
129 stale agent worktrees found this session are exactly this failure mode
accumulated. There is no reconcile path.

Design (crash-consistency + reconciliation):
- ATOMIC ledger writes: every tickets.md mutation is write-temp + fsync +
  atomic rename (never a partial file), so the ledger is always readable and
  consistent to its last completed write. Verify/enforce in frob.tickets._store.
- INTENT JOURNAL for multi-step ops: `frob ticket land`
  (merge+REL-bump+stamp+native-rebuild+close) and any op touching >1 artifact
  writes a small intent record BEFORE starting (.frob/journal/) and clears it
  on success. A crash mid-land leaves the intent record; recovery detects
  "land of T-#### was in flight" and rolls forward (finish) or back (abort
  cleanly) rather than leaving a half-merged tree.
- `frob ticket reconcile` (or a frob doctor extension) scans for:
  - in-progress tickets whose worktree is GONE or whose lease is STALE (no
    sweep/commit/activity in N; agent presumed dead) -> release the lease and
    revert to queued (or a new `stalled` state) with an audit note, freeing
    its scope for others (T-0453).
  - dirty/abandoned worktrees under .claude/worktrees/ not tied to a live
    agent -> offer to remove (the 129-worktree cleanup as a first-class
    command instead of a manual `git worktree remove` loop).
  - orphaned intent-journal records -> resume or abort.
  - half-recorded evidence / in-progress-with-evidence-but-no-Done-report
    after the worktree vanished -> surface for a decision, never auto-close.
- Idempotency: start/evidence/close/scope-change each safe to re-run after a
  crash (a second `frob ticket start` is already a no-op; extend the same to
  evidence dedup and land steps).
- Acceptance: kill an agent mid-work (in-progress ticket + deleted worktree);
  `frob ticket reconcile` detects it, releases the lease, reverts to
  queued/stalled with an audit note, and the freed scope re-appears in
  doable. A simulated crash mid-land (intent record present, merge
  incomplete) is detected and cleanly resolved. The ledger is never left
  unreadable. Relates: T-0453 (lease), T-0455 (scope/lease mutation), T-0431
  (worktree-lease guard), and the stale-worktree cleanup done by hand this
  session.