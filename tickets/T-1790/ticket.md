---
id: T-1790
title: Refuse (or warn on) creating a nested agent worktree under another worktree
  (T-1779 finding 7, source)
state: queued
kind: bug
origin: human
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_lifecycle.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1779 finding 7's root-cause half, filed separately per that finding's
own instruction ("if item 3 is more than a small guard, land 1 and 2 and
file 3 separately").

T-1766's lease named a worktree NESTED under another agent's own
worktree (`.../agent-a421819.../.claude/worktrees/t-1766`). This is
structurally doomed from creation: it cannot land cleanly (the
"nested-worktree lands don't stick" failure mode that has now caught
four agents per the coordinator's own count), and it dies silently the
moment its PARENT worktree is retired/removed -- taking the nested
worktree with it while its lease file survives untouched, orphaning the
ticket it was holding (see the sibling finding-7 ticket for the
detection/release fix for the SYMPTOM; this ticket is the SOURCE).

`frob ticket work` (`frob.app.ticket_runner`, the command that creates a
per-ticket worktree, likely `_lifecycle.py` or wherever the default
worktree path is computed) should refuse to create a worktree whose
resolved path lies under another EXISTING `.claude/worktrees/` entry --
or, at minimum, log a loud warning/gate finding when it does, so the
doomed lease is visible at CREATION time rather than discovered only
when its parent disappears.

Not scoped/sized yet -- filed for triage, not pre-committed to a specific
fix shape (the exact right refusal point needs a look at how `frob
ticket work`/`_default_work_worktree` resolves its path today).
