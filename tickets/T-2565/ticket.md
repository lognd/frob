---
id: T-2565
title: hook header comment and _OURS_MARKER name a nonexistent 'frob scaffold install-worktree-lease-hook'
  command
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/scaffold/project.py
- src/frob/scaffold/_managed.py
evidence_scope:
- tests/test_scaffold_worktree_lease_hook.py
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
evidence:
- tests/test_scaffold_worktree_lease_hook.py::TestOursMarkerMigration::test_current_marker_names_a_real_command
- tests/test_scaffold_worktree_lease_hook.py::TestOursMarkerMigration::test_a_foreign_hook_is_not_claimed
- tests/test_scaffold_worktree_lease_hook.py::TestOursMarkerMigration::test_installed_hook_carries_the_current_marker
- tests/test_scaffold_worktree_lease_hook.py::TestOursMarkerMigration::test_a_legacy_installed_hook_is_reported_stale_not_foreign
designated_repro_test: tests/test_scaffold_worktree_lease_hook.py::TestOursMarkerMigration::test_current_marker_names_a_real_command
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 9e188747ee70066efe420fb329db57b90cc92ebb
---
Found while fixing T-2556. The installed worktree-lease hook's own header
comment, and the constant that matches it, both name a command that does not
exist:

<!-- frob:waive DOC006 reason="quoting the exact stale marker text this ticket RETIRES -- a historical record of the defect, not a live invocation; the real installer is named two lines below" -->
    src/frob/scaffold/project.py:384  # Installed by `frob scaffold install-worktree-lease-hook` (T-0431).
<!-- frob:waive DOC006 reason="quoting the exact stale marker text this ticket RETIRES -- a historical record of the defect, not a live invocation; the real installer is named two lines below" -->
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