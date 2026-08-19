---
id: T-2565
title: hook header comment and _OURS_MARKER name a nonexistent 'frob scaffold install-worktree-lease-hook'
  command
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/scaffold/project.py
- src/frob/scaffold/_managed.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/scaffold/project.py
  reason: the matched-pair marker strings live in exactly these two files
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/scaffold/_managed.py
  reason: the matched-pair marker strings live in exactly these two files
  actor: logan
  at: '2026-08-18'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while fixing T-2556. The installed worktree-lease hook's own header
comment, and the constant that matches it, both name a command that does not
exist:

    src/frob/scaffold/project.py:384  # Installed by `frob scaffold install-worktree-lease-hook` (T-0431).
    src/frob/scaffold/_managed.py:172 _OURS_MARKER = "# Installed by `frob scaffold install-worktree-lease-hook` (T-0431)."

`frob scaffold` exposes only list/apply/new/pool -- verified against
`frob scaffold apply --help`. The real installer is `frob scaffold apply`
(the function is `install_worktree_lease_hook`, not a CLI verb). The same
stale text in T-2556's own ticket body DID fire DOC006 as an ERROR and had to
be fixed before that ticket could land, so this is the identical defect in a
place the gate does not currently reach.

WHY IT WAS LEFT: the two strings are a MATCHED PAIR. `_OURS_MARKER` is how
frob recognises a hook it owns, so changing one without the other makes every
already-installed hook stop being recognised as frob-owned. That needs a
deliberate migration (accept both the old and new marker for a release, then
retire the old one), and `_managed.py` is outside T-2556's declared scope.

DELIVERABLE: retire the nonexistent command from both strings together, with
`_OURS_MARKER` matching the old text as well as the new one so existing
installed hooks keep being recognised.
