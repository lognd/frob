---
id: T-2122
title: 'Id allocation reads taken-ids from a stale merge-base view, so allocator_lock
  serializes writers that disagree: 11 collisions this session, and renumbering to
  escape one collided again'
state: done
kind: bug
origin: human
created: '2026-08-11'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_new_renumber.py
- src/frob/tickets/_draft_finalize.py
- tests/unit/test_process_lock.py
- tests/test_tickets_collision.py
- tests/test_tickets_ledger_concurrency.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_draft_finalize.py
  reason: draft promotion (finalize_draft) imports _next_ticket_id directly from _new_renumber.py
    and is the exact call path the incident's repeated collision (T-draft-ebc58e33
    -> T-2114 -> T-2118) went through; fixing allocation's stale-read root cause requires
    this caller to pass root through to the new shared-counter primitive too, or the
    fix is incomplete for the reported incident
  actor: logan
  at: '2026-08-11'
- op: add
  glob: tests/unit/test_process_lock.py
  reason: 'evidence: repro test for the collision + allocator-lock''s own existing
    coverage, both live under these files'
  actor: logan
  at: '2026-08-11'
- op: add
  glob: tests/test_tickets_collision.py
  reason: 'evidence: repro test for the collision + allocator-lock''s own existing
    coverage, both live under these files'
  actor: logan
  at: '2026-08-11'
- op: add
  glob: tests/test_tickets_ledger_concurrency.py
  reason: TestPromoteVsLandFinalizeAllocationRace monkeypatches frob.tickets._draft_finalize._next_ticket_id
    by name; T-2122 renamed that call site's target to _next_ticket_id_shared(root,
    existing) so the monkeypatch target and wrapper signature must be updated to match,
    or this pre-existing passing test breaks with AttributeError
  actor: logan
  at: '2026-08-11'
- op: add
  glob: design/frob.strata
  reason: SELFAUDIT001/SYS100 fires because the shared id-counter's fs.write (tickets_ledger)
    and the repro test's exec/fs.write (testsuite) capabilities are undeclared; the
    waive clause for this design-level rule lives in design/frob.strata itself (waive
    "SYS100:<node>" syntax), not a source-file frob:waive comment
  actor: logan
  at: '2026-08-11'
evidence:
- tests/unit/test_process_lock.py::TestSharedIdCounter::test_two_checkouts_with_divergent_views_never_collide
designated_repro_test: tests/unit/test_process_lock.py::TestSharedIdCounter::test_two_checkouts_with_divergent_views_never_collide
acceptance:
- text: given two allocators with divergent (stale) views of which ids are taken,
    when both allocate a fresh id concurrently or sequentially against the same repo,
    then they must not receive the same id -- this test MUST fail against current
    main
  evidence:
  - tests/unit/test_process_lock.py::TestSharedIdCounter::test_two_checkouts_with_divergent_views_never_collide
threat: null
component: null
anchor: false
anchor_reason: null
---
