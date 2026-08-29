---
id: T-3297
title: Missing merge driver for frob-managed ledger files causes MergeConflict at
  land
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_land_git_ops.py
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
REPORTED FROM REAL CONSUMER USE (../diax FROBLEMS.md F-038, F-045-first [the
repo has a duplicate F-045 heading -- this is the one titled "every land now
conflicts on frob-coverage.lock.json and tickets/<id>/ticket.md"]).

ROOT CAUSE: frob's land flow merges main into a landing worktree before
merging the worktree's branch, and two frob-managed tracked paths routinely
diverge between main and the worktree in ways plain git 3-way merge cannot
resolve:
  (1) tickets/<id>/ticket.md -- main's mirrored copy (see the already-filed
      close-mirrors-before-land family, F-033/F-034, covered by T-3288 and
      its sibling) can say state=in-progress while the worktree's own copy
      says state=done, or a sibling ticket filed in the worktree and DROPPED
      on main has genuinely different content on each side.
  (2) frob-coverage.lock.json -- both sides re-stamp it independently
      (see the coverage-lock cluster ticket filed alongside this one), so a
      land routinely hits a real content conflict on a file neither side
      edited semantically.

REPORTED IMPACT:
  - F-045-first: land aborts with MergeConflict on both files and leaves the
    worktree mid-merge. A naive `git add -A` after manual conflict resolution
    was observed to commit LITERAL CONFLICT MARKERS into ticket.md, which
    frob later parsed without erroring -- unclear whether/how it errors on
    malformed frontmatter here, worth confirming as part of this fix.
  - F-038: a ticket filed from a worktree and dropped on main (a normal
    "out-of-scope discovery, coordinator drops it" flow) makes the NEXT land
    for the filing ticket refuse with MergeConflict because tickets/<new>/
    ticket.md differs word-for-word between main (dropped) and the worktree
    (queued). Manual recovery: merge main into the worktree, then
    `git checkout main -- tickets/<new>/ticket.md`.

WHAT NOT TO DO: do not silently prefer "worktree wins" for every conflicting
path without checking WHAT changed -- a worktree's stale copy of a ticket
that was legitimately dropped by someone else in the meantime must not
resurrect it. Do not paper over this with `git checkout --theirs` in the
land script; that is exactly the "commits conflict markers silently" failure
mode already observed, just automated.

WHAT TO BUILD: a real merge driver (git attributes + a small resolver, or a
pre-merge step in frob's own land code) for both frob-managed files:
  - tickets/<id>/ticket.md: resolve by LEDGER STATE PRECEDENCE, the way the
    v1 single-file merge driver already did (done/dropped beats
    queued/in-progress; a state transition is monotonic) -- not a textual
    3-way merge.
  - frob-coverage.lock.json: resolve by REGENERATING from whichever side's
    coverage run is authoritative for this land (or dropping it from the
    pre-land snapshot's staged set entirely and letting --stamp-coverage
    regenerate post-merge), never by textual merge.

MUST-FIRE FIXTURE: two branches that each independently mutated
tickets/T-X/ticket.md's state (one to done, one still in-progress) merged
through the new driver -- result must be the later/terminal state, never
conflict markers in the committed file.

MUST-STAY-QUIET FIXTURE: an ordinary land where neither file diverged
between main and the worktree -- must merge cleanly with no new prompts.
