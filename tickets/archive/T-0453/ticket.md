---
id: T-0453
title: 'collision-aware doable: frob ticket doable must exclude queued tickets whose
  scope overlaps any IN-PROGRESS ticket (scope-lease model) so parallel agents never
  collide -- stop hand-maintaining blocklists'
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
- docs/modules/tickets.md
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets_lease.py::TestBreadthPerf::test_breadth_context_uses_git_ls_files_when_available
- tests/test_tickets_lease.py::TestLeasedBy::test_precise_in_progress_does_not_hide_disjoint
- tests/test_tickets_lease.py::TestLargeGlobWarnings::test_silent_on_precise_test_file
designated_repro_test: null
threat: null
component: null
---
User request 2026-07-20: stop the coordinator hand-maintaining collision
blocklists and manually checking whether a doable ticket overlaps in-flight
work. `frob ticket doable` already knows which tickets are IN-PROGRESS (an
agent started them) and every ticket's declared `scope` -- so it should
compute collisions itself and only surface tickets that are BOTH unblocked
AND scope-disjoint from all in-flight work. This session the coordinator
dispatched ~30 parallel agents and hand-derived a growing blocklist every
time; that is exactly the friction frob should own.

Design (scope-lease model):
- A ticket is IN FLIGHT when state == in-progress. Its `scope` globs are an
  active LEASE on those paths.
- `frob ticket doable` (default) EXCLUDES any queued/planned ticket whose
  scope overlaps the union of all in-flight leases. Overlap = glob-set
  intersection: two scopes collide if any concrete path could match a glob
  in both (compute via path-prefix/fnmatch intersection; a dir glob
  `src/frob/gates/**` collides with `src/frob/gates/_arch.py` and with
  `src/frob/**`). tickets.md itself is implicitly leased by every ticket, so
  IGNORE it in overlap (the T-0323 merge driver already resolves the ledger)
  -- otherwise everything collides.
- Broad-scope handling: a very broad lease (`src/frob/**`) would block
  almost everything. Options to pick: (a) warn that a broad in-flight scope
  is serializing the queue, (b) a per-ticket `--allow-overlap` opt-out,
  (c) an explicit `frob ticket doable --ignore-lease` to see the raw list.
  Default stays collision-safe.
- Show WHY a ticket is held back: `frob ticket doable --show-blocked` lists
  excluded tickets with the in-flight ticket + overlapping path that leases
  it (so the coordinator sees "T-0xxx held: scope src/frob/gates/** leased
  by in-progress T-0yyy").
- Ties into T-0431 (worktree-lease guard): starting a ticket acquires the
  lease; the lease releases on close/fail/abandon. A stale in-progress
  ticket (agent died) should be reap-able (`frob ticket doable` could flag
  leases older than N with no recent sweep as stale).
- Acceptance: with T-A in-progress (scope src/frob/gates/**), `frob ticket
  doable` never returns a queued ticket scoped into src/frob/gates/**;
  closing T-A re-surfaces them; a disjoint-scope ticket is always returned;
  --show-blocked explains each exclusion. The coordinator can then dispatch
  straight off `doable` with zero manual collision-checking.

DESIGN CORRECTION (user 2026-07-20, after a first implementation over-hid):
a first cut made `frob ticket doable` return 0 because nearly every ticket
declares a BROAD `tests/**` (and often `docs/`) in scope, so any in-progress
ticket leased the whole test/doc tree and collided with everything. The
WRONG fix is to ignore tests/** in the overlap (that masks real test-file
collisions). The RIGHT fix, per the user:
- Keep the lease-overlap logic SOUND (real path/glob intersection; only
  tickets.md stays ignored, since the T-0323 merge driver owns it). Do NOT
  special-case tests/**/docs/ out of the check.
- Fix it at the SCOPE-DECLARATION level: a ticket should scope the SPECIFIC
  files it touches (tests/test_gates.py), not the broad tests/**. Add a
  LARGE-GLOB WARNING -- a check that flags any ticket whose scope contains an
  over-broad glob (tests/**, src/frob/**, docs/, docs/**, or a glob matching
  more than a tunable N files) and nudges narrowing it to the precise files.
  This makes leases precise AND makes every ticket's scope an honest
  statement of what it touches (accountability), tunable via frob.toml.
- With precise scopes, the lease filter stops over-hiding naturally: a ticket
  scoped tests/test_gates.py only collides with another ticket touching that
  same file (a REAL collision); two tickets adding different test files no
  longer collide. Existing ~100 broad-scope tickets are SURFACED by the
  warning for narrowing, not migrated wholesale in this ticket.
- Tests: (a) large-glob warning fires on tests/** scope, silent on
  tests/test_x.py; (b) precise-scoped in-progress tickets do not over-hide
  disjoint queued tickets; (c) a real source+precise-test collision IS
  hidden; and verify `frob ticket doable` on the real repo returns a sensible
  non-empty list with in-progress tickets present.