---
id: T-1552
title: 'ledger v2: delete v1 splice machinery once main is migrated'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: critical
blocked_by:
- T-1631
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land_ledger_merge.py
- src/frob/tickets/_land_merge.py
- src/frob/tickets/_land_merge_zones.py
- .gitattributes
- docs/modules/tickets.md
- docs/design/ledger-v2.md
- tickets.md
- src/frob/tickets/_store.py
- src/frob/tickets/_draft_finalize.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tickets.md
  reason: 'Owner directive 2026-08-08: remove tickets v1, v2 is battle-tested. The
    v1 monofile tickets.md (545KB) is the primary deletion target and was not in scope;
    _store.py still carries v1 readers and _draft_finalize.py the v1 promote path.
    Deleting the splice machinery without the file it splices leaves the artifact
    on main.'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/tickets/_store.py
  reason: 'Owner directive 2026-08-08: remove tickets v1, v2 is battle-tested. The
    v1 monofile tickets.md (545KB) is the primary deletion target and was not in scope;
    _store.py still carries v1 readers and _draft_finalize.py the v1 promote path.
    Deleting the splice machinery without the file it splices leaves the artifact
    on main.'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/tickets/_draft_finalize.py
  reason: 'Owner directive 2026-08-08: remove tickets v1, v2 is battle-tested. The
    v1 monofile tickets.md (545KB) is the primary deletion target and was not in scope;
    _store.py still carries v1 readers and _draft_finalize.py the v1 promote path.
    Deleting the splice machinery without the file it splices leaves the artifact
    on main.'
  actor: logan
  at: '2026-08-08'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
## Description

T-1491 (final cutover) deliberately did NOT delete the v1 splice
machinery (`_render_ledger`, `splice_ledger` in
`src/frob/tickets/_land_ledger_merge.py`, `_land_merge.py`,
`_land_merge_zones.py`, the `tickets.md`/`tickets-archive.md`
`.gitattributes` merge-driver lines) because this repo's OWN ledger is
still v1-mode as of T-1491's session -- every ticket mutation across a
multi-agent dispatch still depends on `splice_ledger` via the registered
git merge driver. Deleting the machinery before this repo's own
`tickets.md`/`tickets-archive.md` content is actually migrated to v2
(via `frob ticket migrate` once the v1-to-v2 migrator is CLI-wired --
see T-1492) would break every in-flight worktree's ticket operations
immediately.

## Plan

Blocked on: T-1492 (CLI wiring for `frob ticket migrate --to v2`), the
follow-up default-flip ticket (T-1553, renumbers at land), and
a coordinator-chosen quiet window (per this ticket's own stated
precondition) to actually run the migration against this repo's real
`tickets.md`/`tickets-archive.md`.

1. Coordinator runs `frob ticket migrate --to v2` against this repo in a
   quiet window (zero in-flight worktrees).
2. Observe the LEDGERV1001 deprecation window for the recorded interval.
3. Delete `_render_ledger`, `splice_ledger`, `_land_merge.py`,
   `_land_merge_zones.py`, remove the `.gitattributes` merge-driver
   lines, remove `tickets.md`/`tickets-archive.md` from the repo (or
   archive them as historical artifacts per the coordinator's call).

## Acceptance

- [ ] GIVEN this repo's own ledger has been migrated to v2 in a quiet
      window WHEN this ticket lands THEN `_render_ledger`, `splice_ledger`,
      `_land_merge.py`, `_land_merge_zones.py`, and the `.gitattributes`
      merge-driver lines no longer exist, and `frob check` reports zero
      references to any of them.

## Failure log
- 2026-08-08 attempt 1: premise not yet true: LEDGERV1001 sunset 2027-02-02 not reached, deletion would preempt own recorded deprecation window
- 2026-08-10 attempt 2: blocked: 8 of 9 frob-wired sibling repos still v1-mode; v1 splice machinery is generic per-root code they depend on, not this-repo-scoped; see draft T-1971
