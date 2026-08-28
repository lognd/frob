---
id: T-2646
title: 938 stale local branches are accumulated debt -- needs a stranded-work analysis
  before pruning
state: done
kind: feature
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/guides/agent-playbook.md
- scripts/branch_stranded_work_analysis.py
- docs/audits/branch-stranded-work-2026-08-25.md
- tests/unit/test_branch_stranded_work_analysis.py
- tickets/T-2915/ticket.md
- tickets/T-2914/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: scripts/branch_stranded_work_analysis.py
  reason: T-2646 needs a new classification script + its output report; not covered
    by the default agent-playbook.md scope
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/audits/branch-stranded-work-2026-08-25.md
  reason: T-2646 needs a new classification script + its output report; not covered
    by the default agent-playbook.md scope
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/unit/test_branch_stranded_work_analysis.py
  reason: unit tests for the new classification script
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tickets/T-2915/ticket.md
  reason: tickets filed from this worktree during T-2646's analysis
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tickets/T-2914/ticket.md
  reason: tickets filed from this worktree during T-2646's analysis
  actor: logan
  at: '2026-08-25'
evidence:
- tests/unit/test_branch_stranded_work_analysis.py::TestClassifyBranch::test_merged_when_ancestor
- tests/unit/test_branch_stranded_work_analysis.py::TestClassifyBranch::test_ticket_done_when_all_ids_terminal
- tests/unit/test_branch_stranded_work_analysis.py::TestClassifyBranch::test_stranded_when_ticket_not_terminal
- tests/unit/test_branch_stranded_work_analysis.py::TestClassifyBranch::test_stranded_when_no_ticket_signal_but_real_diff
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 3cb9f604fac997817848b00d05beab757b5add62
---
This repo currently carries 938 local branches against 35 worktrees
(measured during T-2629, 2026-08-19) -- branches outnumber worktrees
~27x. Most correspond to landed or abandoned agent work and are never
cleaned up. Even a FAST scan over 938 branches is wasted work, and this
is exactly the scale that made T-2629's inline unlanded-branch-work scan
inside `frob ticket doable` structurally unable to complete.

Filed separately per T-2629's own instruction not to fold this in.
Related to, but distinct from, T-2599/T-2617's worktree audit (35
worktrees, 0 STRANDED at last measurement) -- that covered worktree
registrations, not the much larger set of local branches.

Do NOT delete branches as part of this ticket's filing -- deleting
branches is destructive and needs its own stranded-work analysis (which
branches are genuinely landed/abandoned vs. still live), exactly like the
worktree audit did before removing anything. This ticket is the analysis
step: enumerate branches, classify each as landed / abandoned / live /
unknown against `main`, and produce a pruning plan (or a
`frob worktree sweep`-shaped mechanism extended to branches) before any
deletion happens.