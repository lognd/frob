---
id: T-0836
title: 'worktree sweep command: lease-aware stale-worktree cleanup (raw git sweep
  destroyed a live agent env)'
state: done
kind: feature
origin: human
created: '2026-07-23'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner.py
- src/frob/tickets/_leases.py
- docs/guides/agent-playbook.md
- tests/test_ticket_leases.py
- src/frob/app/worktree_runner.py
- src/frob/__main__.py
- README.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/worktree_runner.py
  reason: "T-0836 CLI wiring requires two files outside the declared scope, following\n\
    the ticket's own precedent (`frob agent`/`frob bind`, self-contained\nrunner dispatched\
    \ directly by `__main__._dispatch`):\n\n- src/frob/app/worktree_runner.py: new\
    \ self-contained CLI runner for\n  `frob worktree sweep`, mirroring src/frob/app/agent_runner.py.\n\
    - src/frob/__main__.py: register the `worktree` subcommand for --help\n  discovery\
    \ and add the direct-dispatch branch in `_dispatch`, mirroring\n  the existing\
    \ `bind`/`agent` branches.\n\nBoth are minimal, mechanical additions with no other\
    \ behavior change.\n"
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/__main__.py
  reason: "T-0836 CLI wiring requires two files outside the declared scope, following\n\
    the ticket's own precedent (`frob agent`/`frob bind`, self-contained\nrunner dispatched\
    \ directly by `__main__._dispatch`):\n\n- src/frob/app/worktree_runner.py: new\
    \ self-contained CLI runner for\n  `frob worktree sweep`, mirroring src/frob/app/agent_runner.py.\n\
    - src/frob/__main__.py: register the `worktree` subcommand for --help\n  discovery\
    \ and add the direct-dispatch branch in `_dispatch`, mirroring\n  the existing\
    \ `bind`/`agent` branches.\n\nBoth are minimal, mechanical additions with no other\
    \ behavior change.\n"
  actor: logan
  at: '2026-07-23'
- op: add
  glob: README.md
  reason: 'The new `frob worktree` subcommand trips this repo''s own DOC005 drift-

    lock gate (README.md''s command table is statically checked against the

    live subcommand registry): adding a real subcommand with no matching

    README row/count update fails `frob check`. README.md needs one new

    table row (under Setup, alongside `frob agent`) and its claimed command

    count bumped by one -- a minimal, mechanical addition, not a rewrite.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_ticket_leases.py::TestListAgentWorktrees::test_lists_only_dot_claude_worktrees_paths
- tests/test_ticket_leases.py::TestSweepWorktrees::test_clean_no_lease_removed
- tests/test_ticket_leases.py::TestSweepWorktrees::test_clean_live_lease_kept
- tests/test_ticket_leases.py::TestSweepWorktrees::test_dirty_kept
- tests/test_ticket_leases.py::TestSweepWorktrees::test_expired_lease_clean_removed
- tests/test_ticket_leases.py::TestSweepWorktrees::test_dry_run_removes_nothing
- tests/test_ticket_leases.py::TestSweepWorktrees::test_branches_survive_removal
- tests/test_ticket_leases.py::TestSweepWorktrees::test_min_age_keeps_recent_worktree
- tests/test_ticket_leases.py::TestWorktreeSweepCli::test_sweep_cli_prints_verdicts_and_summary
designated_repro_test: null
threat: null
component: null
---
Hit live 2026-07-23: coordinator hand-swept 68 stale worktree
registrations with raw `git worktree remove`; the skip-list missed a live
agent's CLEAN worktree (read-only diagnosis phase, nothing uncommitted)
and destroyed its environment mid-run. git's own dirty-refusal is not a
liveness check -- a live agent between writes looks clean.

Fix: add `frob worktree sweep` that enumerates registered agent
worktrees and removes ONLY those that are (a) clean AND (b) hold no live
lease for any non-terminal ticket (reuse _probe_worktree_liveness /
resolve_lease pinning) AND (c) optionally older than --min-age. Print a
per-worktree verdict (removed / kept:lease / kept:dirty / kept:age).
Never delete branches. Coordinator playbook + docs updated to forbid raw
git-level sweeps.