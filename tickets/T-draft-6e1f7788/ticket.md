---
id: T-draft-6e1f7788
title: 'frob check cache.db/parse-artifacts.db: database is locked under concurrent
  checks'
state: queued
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/cache.py
- docs/modules/graph.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/_cache.py
  reason: 'correct scope: cache.connect/database-is-locked lives in graph/cache.py,
    not gates'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/graph/cache.py
  reason: 'correct scope: cache.connect/database-is-locked lives in graph/cache.py,
    not gates'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: docs/modules/graph.md
  reason: doc anchor closure for graph/cache.py symbols
  actor: logan
  at: '2026-08-27'
body_changes:
- mode: set
  reason: record full captured repro + plan
  actor: logan
  at: '2026-08-27'
  old_length: 0
  new_length: 4388
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## 4. Separate, likely more important finding: sqlite cache lock errors under concurrent `frob check`

Captured during the SAME window (concurrent T-3115 land + fleet checks),
command: `frob check --ticket T-3122` (also independently reproduced
error text via `frob check --delta --ticket T-3122` moments later, this
one recovered/rebuilt rather than hard-failing):

    WARNING: frob check: 6 other check(s) already running on this host -- see `scripts/fleet_status.py` for swap/load before dispatching more (T-2473, advisory only -- this check is not deferred)
    WARNING: cache.connect: unreadable db at /home/logan/projects/frob/.claude/worktrees/t-3122/.frob/cache.db, rebuilding: no such table: meta
    ...
    WARNING: cache.connect: unreadable db at /home/logan/projects/frob/.claude/worktrees/t-3122/.frob/parse-artifacts.db, rebuilding: no such table: meta
    ...
    ERROR: main: unhandled exception during dispatch: database is locked
    frob: database is locked

This is a HARD failure (nonzero exit, "unhandled exception during
dispatch"), not a warning-and-recover -- the FIRST `frob check --ticket
T-3122` invocation in this session died outright with `database is
locked` after the two "unreadable db ... rebuilding: no such table: meta"
warnings on cache.db and parse-artifacts.db. The immediately-following
retry of the same command succeeded normally. This happened while
`fleet_status` was reporting 6 concurrent `frob check` runs on the host,
plus a live `frob ticket land T-3115` in the shared root.

Corroborating signal from the coordinator: `fleet_status` independently
reports CONCURRENT CHECKS: 6 on this host even during an otherwise-quiet
window, so this is not a one-off level of contention -- it is close to
ambient here.

This is filed as the higher-priority candidate ticket once the land
window clears: an unhandled `database is locked` crash under ordinary
(not even unusual) concurrent-check load in a per-worktree sqlite cache
(cache.db / parse-artifacts.db) is a real defect regardless of whether
the close-guard false-fire above ever reproduces, and is a plausible
root-cause mechanism for it (a torn/stale cache read serving a wrong
`Ticket.body` or wrong comparison result exactly once under the same
contention).

## Description + plan

`frob check` (via `src/frob/graph/cache.py::connect`) can crash outright
with an unhandled `database is locked` sqlite3 exception under ordinary
concurrent load -- multiple `frob check` invocations plus a live `frob
ticket land` on the same host, not an unusual or contrived scenario (the
fleet's own `fleet_status` independently reports ~6 concurrent checks on
this host even during an otherwise-quiet window, so this level of
contention is close to ambient here, not a rare spike).

Captured live during T-3122 (series BT) work: the FIRST `frob check
--ticket T-3122` invocation of the session died with `ERROR: main:
unhandled exception during dispatch: database is locked` / `frob:
database is locked`, preceded by two `cache.connect: unreadable db ...
rebuilding: no such table: meta` warnings against
`.frob/cache.db` and `.frob/parse-artifacts.db`. The immediately-following
retry of the IDENTICAL command succeeded normally with no special
handling on my part.

Plan: `connect`/`connect_readonly` in `src/frob/graph/cache.py` need to
tolerate a locked/mid-rebuild sqlite file under concurrent access --
either a bounded retry-with-backoff around the `sqlite3.OperationalError:
database is locked` case, a `busy_timeout` PRAGMA set on connect, or
(if concurrent writers to the same per-worktree cache file is the actual
root cause) serializing writers with a lock file / WAL mode, whichever
the current schema/access pattern supports without a wider rework. The
"rebuilding: no such table: meta" warnings immediately preceding the
crash suggest the failure may be specifically a rebuild-in-progress
racing a second reader/writer against the same file, which strengthens
the case for either serializing the rebuild step or using WAL mode so
reads are not blocked by a writer's rebuild.

This is also flagged as a PLAUSIBLE mechanism for a separate one-off
finding (T-3122's close guard false-firing exactly once under the same
concurrent-load window, never reproduced since) -- filed separately,
referencing this ticket, since that one is unconfirmed and this one is
directly, repeatably captured.
