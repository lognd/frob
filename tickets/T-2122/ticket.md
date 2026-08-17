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
land_commit: null
---
## Done report

Changed:
- src/frob/tickets/_new_renumber.py::_shared_id_counter_path (new)
- src/frob/tickets/_new_renumber.py::_next_ticket_id_shared (new)
- src/frob/tickets/_new_renumber.py::_max_ticket_number (new, split out of _next_ticket_id)
- src/frob/tickets/_new_renumber.py::_next_ticket_id (kept, now the pure/fallback scan only)
- src/frob/tickets/_new_renumber.py::_allocate_ticket_id (routes the default-branch case through _next_ticket_id_shared)
- src/frob/tickets/_draft_finalize.py::finalize_draft (routes through _next_ticket_id_shared(root, ...))
- src/frob/tickets/_draft_finalize.py::_finalize_draft_for_land_locked (routes through _next_ticket_id_shared(main_root, ...))
- design/frob.strata (capability declarations: tickets_ledger fs.write for _new_renumber.py; testsuite exec/fs.write for tests/unit/test_process_lock.py -- SYS111 ratchet ceiling left for land's own fix_sys111_capability_ratchet_sync Tier-A auto-fix per docs/modules/gates.md)
- tests/test_tickets_ledger_concurrency.py::TestPromoteVsLandFinalizeAllocationRace (renamed monkeypatch target from the old _next_ticket_id to _next_ticket_id_shared, two-arg wrapper -- pre-existing test broken by the rename, not new coverage)

Evidence:
- tests/unit/test_process_lock.py::TestSharedIdCounter::test_two_checkouts_with_divergent_views_never_collide (--accepts 0, designated repro: FAILED_AT_PARENT at c366a59f2, confirmed with --check-repro)
- tests/unit/test_process_lock.py full file: 21 passed (was 19 before this ticket; +2 new tests -- test_two_checkouts_with_divergent_views_never_collide, test_counter_file_lives_under_git_common_dir)
- tests/test_tickets_ledger_concurrency.py: 6 passed (unchanged count, repaired monkeypatch target)
- tests/test_tickets_collision.py: 24 passed (unchanged, no regressions)
- tests/test_tickets.py: 161 passed (unchanged, no regressions)
- tests/system/test_cli_ticket_promote.py + tests/test_ticket_leases_cross_worktree.py + tests/test_ticket_leases.py: 157 passed (unchanged, no regressions)

Root cause and fix (for the pattern classification the coordinator asked about):
`allocator_lock` (T-1253) locks `<root>/.frob/tickets-allocator.lock` -- a
PER-CHECKOUT path, not shared across worktrees, so two different checkouts
(a worktree and the primary root, or two worktrees) never actually
contended on it; `_next_ticket_id` then computed "next" purely from
whatever `existing`/`merged` snapshot its own caller happened to hold, with
no way to see a sibling checkout's not-yet-landed claim (finalize_draft_
for_land commits a promoted draft's new id to the WORKTREE being landed,
not main, until the squash-merge moments later -- a concurrent new_ticket
reading main's ledger in that window correctly sees the id as free). Wider
locking cannot close this: even perfectly serialized readers each
correctly conclude "id N is free" from their own current-at-the-time view.
The fix replaces the tree-scan with a single counter file at
<git-common-dir>/frob-ticket-id-counter (T-0473's frob-leases precedent
for "the one place every checkout of this clone shares"), flocked
directly for its own read-increment-write -- every allocation claims from
the SAME physical file regardless of checkout, so the counter (not
ledger content) is now the single source of truth for "has this id been
claimed."

Filed: none (no out-of-scope discoveries beyond the coupled test-file
repair already listed above, which was pulled into this ticket's own
scope since it was a direct, unavoidable consequence of the rename).

Gates: frob check --ticket T-2122 clean except:
  - gate:SELFAUDIT SYS111 (exec/fs.write via-list ratchet ceiling on testsuite
    and tickets_ledger) -- left for frob ticket land's own pre-land Tier-A
    fix_sys111_capability_ratchet_sync auto-fix (docs/modules/gates.md's
    "Tier-A deterministic auto-fix handlers" section), which self-heals
    this exact shape when the SYS100 via-list widening (already applied
    here) lands in the same pass.
  - gate:TICK TICK004 (pre-existing repo-wide backlog rot, unrelated).
  - ruff-format (114 files repo-wide, pre-existing) and one unrelated
    E501 in src/frob/gates/_root_asset_dirs.py (pre-existing, not a
    touched file).
  gate:ARCH/gate:AFFECT/gate:DOC/gate:DRIFT/gate:SCOPE/ty/ruff-check on
  touched files: all clean.

### Changed
```
 design/frob.strata                       |   6 +-
 src/frob/tickets/_draft_finalize.py      |  21 +++-
 src/frob/tickets/_new_renumber.py        | 159 +++++++++++++++++++++++++++++--
 tests/test_tickets_ledger_concurrency.py |  18 +++-
 tests/unit/test_process_lock.py          |  92 ++++++++++++++++++
 tickets/T-2122/ticket.md                 |  56 ++++++++++-
 6 files changed, 329 insertions(+), 23 deletions(-)
```

### Evidence
- `tests/unit/test_process_lock.py::TestSharedIdCounter::test_two_checkouts_with_divergent_views_never_collide` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/t-2122/src/frob/gates/_root_asset_dirs.py, SELFAUDIT001@design, TICK004@tickets.md
