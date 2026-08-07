---
id: T-0335
title: extend prune-before-descend to remaining os.walk sites (gates secrets/sys/tickets/archgate/prework)
state: done
kind: bug
origin: agent
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/tickets/**
- src/frob/excludes.py
- tickets.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_gates.py
  reason: T-0335 gates work maps to tests/test_gates.py
  actor: logan
  at: '2026-07-20'
evidence:
- tests/test_walk_lint_gate.py::TestHelper::test_walk_pruned_call_is_silent
- tests/test_walk_lint_gate.py::TestSelfMatchExclusion::test_own_files_not_scanned
designated_repro_test: null
acceptance:
- text: given 100+ gitignored nested worktrees under .claude/worktrees/, when frob
    check runs secrets/sys/tickets/archgate/prework, then each prunes excluded/nested-worktree
    dirs before descending (frob.excludes helpers) so wall time drops like T-0239
    did for graph walking, instead of ~350s each
  evidence: []
- text: given the shared frob.excludes prune helpers (T-0239), when a new os.walk
    site is added in gates/tickets, then it reuses them rather than re-deriving the
    rule
  evidence: []
threat: null
component: null
---
T-0239 fixed graph/outline walking but a full frob check still shows archgate/secrets/sys/tickets each ~350s -- these gates have their OWN os.walk/rglob sites (gates/_baseline.py, _coverage.py, _secrets.py, _prework.py, tickets sweep) still descending into every stale worktree. T-0239's Done report flagged this follow-up. Sweep every remaining os.walk/rglob in gates/ and tickets/ onto prune-before-descend using shared frob.excludes helpers (_is_nested_worktree/_should_prune_dir/load_exclude_globs); do NOT duplicate the rule. Verify before/after full-check timing.