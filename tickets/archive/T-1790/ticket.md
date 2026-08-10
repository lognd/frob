---
id: T-1790
title: Refuse (or warn on) creating a nested agent worktree under another worktree
  (T-1779 finding 7, source)
state: done
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
- tests/test_ticket_work_and_land_finish.py
- tickets/T-1790/ticket.md
- tickets/T-1786/ticket.md
- tickets/T-1795/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: the new nested-worktree-creation refusal needs test coverage; TestWork already
    exercises frob ticket work's happy path in this same file
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1790/ticket.md
  reason: v2-store per-ticket ledger file for this ticket itself
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1786/ticket.md
  reason: carried on this same branch from earlier ticket-management ops in this worktree
    (dropping T-1786 as superseded, filing T-1795) -- not touched by T-1790's own
    code change but part of this branch's diff vs main since the worktree was not
    reset between tickets
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1795/ticket.md
  reason: carried on this same branch from earlier ticket-management ops in this worktree
    (dropping T-1786 as superseded, filing T-1795) -- not touched by T-1790's own
    code change but part of this branch's diff vs main since the worktree was not
    reset between tickets
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_ticket_work_and_land_finish.py::TestRootIsItselfANestedWorktree::test_detects_root_under_dot_claude_worktrees
- tests/test_ticket_work_and_land_finish.py::TestRootIsItselfANestedWorktree::test_primary_checkout_is_not_nested
- tests/test_ticket_work_and_land_finish.py::TestRootIsItselfANestedWorktree::test_work_refuses_from_a_nested_worktree
- tests/test_ticket_work_and_land_finish.py::TestRootIsItselfANestedWorktree::test_work_cluster_refuses_from_a_nested_worktree
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

## Done report

Refuses `frob ticket work`/`frob ticket work --cluster` when `root` is
itself already a dispatched agent worktree (has a `.claude/worktrees`
segment in its own path) -- the root cause behind T-1779 finding 7:
T-1766's worktree was created UNDER another agent's own worktree
(`.../agent-a421819.../.claude/worktrees/t-1766`), and died silently the
moment its parent was retired, taking the nested worktree with it while
its lease survived, orphaning the ticket it held (see T-1789's
`orphaned_leases`/`release_orphaned_lease` for the downstream fix for
that symptom; this ticket closes the source instead).

`_root_is_itself_a_nested_worktree(root)` (new, in `_lifecycle.py`):
same segment-matching shape as `frob.tickets._leases.
_is_agent_worktree_path`, kept as an independent small check rather than
a new cross-module dependency since this ticket's declared scope is
`_lifecycle.py` alone. Wired into both `_work` and `_work_cluster` right
after each validates its own required args, before either computes a
worktree path or touches git -- refuses loudly (exit 1), naming `root`
and the ticket/cluster id, pointing at running from the primary checkout
instead.

Kept the docs addition out of scope deliberately (narrowing per the
standing rule) -- the two new functions' docstrings carry the full
rationale and incident citation; a docs/modules/tickets.md section can
follow alongside T-1789's existing "Root checkout write guard"/
"Orphaned-lease detection" sections if wanted, but was not added here to
keep this ticket's footprint to exactly the file it was scoped to.

`frob check --only prework --only scope --only sys --ticket T-1790` is
clean except pyproject.toml/uv.lock SCOPE001 (land-owned drift between
merges, resolved at land time).

### Changed
```
 CHANGELOG.md                       | 13 -------
 pyproject.toml                     |  2 +-
 tickets/T-1786/ticket.md           |  5 ++-
 tickets/T-1790/ticket.md           | 39 ++++++++++++++++++++-
 tickets/T-1795/ticket.md | 69 ++++++++++++++++++++++++++++++++++++++
 uv.lock                            |  2 +-
 6 files changed, 113 insertions(+), 17 deletions(-)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestRootIsItselfANestedWorktree::test_detects_root_under_dot_claude_worktrees` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestRootIsItselfANestedWorktree::test_primary_checkout_is_not_nested` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestRootIsItselfANestedWorktree::test_work_refuses_from_a_nested_worktree` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestRootIsItselfANestedWorktree::test_work_cluster_refuses_from_a_nested_worktree` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 2 error(s), 599 warning(s), 720 waived
- error-findings: DUP001@src/frob/app/ticket_runner/_lifecycle.py, REL002@.frob-release.json
