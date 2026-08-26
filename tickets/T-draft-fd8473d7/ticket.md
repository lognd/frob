---
id: T-draft-fd8473d7
title: frob ticket new blocks up to ~5min on an unrelated land, then strands an uncommitted
  ticket on timeout
state: queued
kind: bug
origin: human
created: '2026-08-25'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_new.py
- src/frob/tickets/_leases.py
- tests/unit/test_ticket_leases.py
- tests/unit/test_ticket_new.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_leases.py
  reason: evidence for the new-ticket-vs-land-lock fix
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/unit/test_ticket_new.py
  reason: evidence for the new-ticket-vs-land-lock fix
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/unit/test_ticket_leases.py
  reason: evidence for the new-ticket-vs-land-lock fix
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/unit/test_ticket_new.py
  reason: evidence for the new-ticket-vs-land-lock fix
  actor: logan
  at: '2026-08-25'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`frob ticket new` (the CLI verb, `frob.app.ticket_runner._new._new`) blocks
for up to the full land-wait budget (currently up to ~313-500s observed,
`_load_land_wait_timeout_s`'s default) on an unrelated `frob ticket land`
holding `LAND_LOCK_REL` in the shared root, then `sys.exit(1)` on timeout.

Root cause, traced directly:

- `new_ticket()` allocates the id and writes the ticket to disk under
  `allocator_lock(root)` + `ledger_lock(root)` (`_allocate_and_write_new_
  ticket`, `_new_renumber.py`) -- id uniqueness is fully guaranteed at
  this point, independent of anything below.
- `_new()` (the CLI wrapper) calls `new_ticket(..., no_commit=True,
  warn_if_dirty=False)` -- the ticket file(s) are ALREADY durably written,
  uncommitted, in `root`'s working tree by this point.
- `_new()` then calls `commit_ticket_ledger_change(root, ticket.id, ...)`
  with no `wait_timeout_s` override, which funnels into
  `_add_and_commit_tickets_md`, which calls `refuse_if_land_in_progress
  (root)` (also no override) BEFORE `git add`/`git commit`. This wait
  uses the full default budget scaled against the in-flight land's own
  start time (`_resolve_land_wait_budget`) -- observed directly this
  session as ~300s+ under real fleet load.
- On timeout, `commit_ticket_ledger_change` returns `Err(LandInProgress)`,
  `_new()` logs and `sys.exit(1)`s -- but the ticket's file(s) are STILL
  on disk, uncommitted, in the shared root (git status dirty). This is
  the SAME DirtyMain hazard class this repo has hit repeatedly (see
  "Retry loop dirties the root" / "Query commands dirty the root" in
  session memory) -- just not yet observed as a filed incident for this
  exact call site.

Is the wait genuinely necessary? Partially, and the reason is git-level,
not ledger-level: `_land_lock` (`_land.py`) wraps `_land_locked`'s ENTIRE
precheck-through-commit body (merge, gate re-verification, tests, squash-
apply, final commit) in ONE process-wide flock for the whole land duration
(median ~95s, p90 ~440s per docs/guides/agent-playbook.md section 13) --
not just the brief window where `root`'s actual git working tree/index is
mutated (squash-apply). `git commit -- tickets.md` (or `tickets/T-####/`)
racing a concurrent `git merge`/`git commit` on the SAME working tree's
index is a real, structural git-level hazard, not merely a ledger-content
race -- id-allocation correctness (`allocator_lock`/`ledger_lock`, T-1253)
is a SEPARATE, already-adequate guard and is untouched by anything here.

A narrower lock scoped to just land's actual root-mutation window (not
its whole duration) would be the ideal fix, but requires restructuring
`_land_lock`'s scope inside `_land_locked` -- a high-risk core-locking
change to a file with a long incident history, explicitly out of a
bug-ticket-sized change.

Proposed narrower fix that IS safe and stays scoped to the ticket-new
call site only: give `_new()`'s `commit_ticket_ledger_change` call (a)
a much shorter `wait_timeout_s` and (b) a clean ROLLBACK of the just-
written, still-uncommitted ticket pathspecs (`_ledger_pathspecs`) on a
`LandInProgress` timeout, before returning Err -- so a fast failure
leaves `root` exactly as clean as before the call (no DirtyMain hazard
introduced, and none of the existing timeout-then-dirty behavior either),
and the id is safely available for reallocation on retry (nothing on
disk still claims it). This trades "wait ~5 minutes, then dirty root
anyway" for "wait ~tens of seconds, clean root, actionable retry" --
strictly better on both axes since rollback removes the dirt risk the
current long wait was implicitly trying to avoid by usually finishing in
time.

Acceptance:
1. `frob ticket new` under a live land returns within a bounded, short
   wait (order tens of seconds, not minutes) instead of the current
   ~300-500s.
2. On that timeout, `git status --porcelain` in `root` is clean --  no
   stranded uncommitted ticket file.
3. N concurrent `frob ticket new` calls (a land in flight throughout)
   produce N distinct ids with no `DuplicateId` -- proven with a real
   concurrent test, not simulated serially.
