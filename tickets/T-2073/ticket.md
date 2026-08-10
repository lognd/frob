---
id: T-2073
title: Split _doable along the decide/IO/format seam (ARCH001 117 lines + ARCH103)
state: queued
kind: feature
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_query.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: given src/frob/app/ticket_runner/_query.py, when frob check --only archgate
    runs, then neither ARCH001 nor ARCH103 is reported for that file (both measured
    present before the change)
  evidence: []
- text: given the doable commands existing test surface, when it runs after the split,
    then it stays green -- a refactor of a load-bearing function needs its callers
    exercised, not just a gate reading zero
  evidence: []
threat: null
component: ticket_runner
anchor: false
anchor_reason: null
---
Floor errors measured unscoped on main, both at
src/frob/app/ticket_runner/_query.py:324:

    ARCH001  function `_doable` has 117 lines (threshold: 60)
    ARCH103  `_doable` mixes I/O, string-formatting, and 8 decision points
             in one body

ARCH103 names the correct seam, so the split follows it rather than chopping
the body at line 60 to get under the threshold (which would clear ARCH001 and
leave ARCH103 firing):

  - I/O steps: queue load, the T-2006 sweep-revalidate, the T-2034-hardened
    write path
  - a pure decision step returning a `_DoableSelection` NamedTuple: the
    `doable()` call, sprint filter, in-flight/dispatchable split, alarm
    ordering
  - render steps: JSON and plain formatting

No behaviour change. T-2034's fix for the query-verb dirty-write bug is
preserved through the split, not altered -- `frob ticket doable` writing to
the shared root and abandoning writes on lock loss DirtyMain-blocked the whole
fleet once already.

Work is already implemented and committed on branch `t2043-query-split`
(worktree .claude/worktrees/t2043-query-split). That branch was authored
before this ticket existed and stamps the placeholder id `T-2043` in 7 places;
`T-2043` is a REAL and unrelated ticket (post-land sweep regression from
T-2023), so every one of those references must be corrected to this ticket's
id before landing, or the obligation graph gains false edges. Note that
`frob ticket renumber` only rewrites `frob:ticket` directive comments, not
free-form prose or commit messages -- check both.
