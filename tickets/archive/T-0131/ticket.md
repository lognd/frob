---
id: T-0131
title: frob ticket resolves repo root to main checkout from inside a linked worktree
  (first invocation)
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_cli_ticket_worktree_root.py::TestTicketRootFromLinkedWorktree::test_new_ticket_no_dot_frob_lands_in_worktree
- tests/system/test_cli_ticket_worktree_root.py::TestTicketRootFromLinkedWorktree::test_ticket_show_reads_worktrees_own_ledger
designated_repro_test: null
threat: null
component: null
---
Found during T-0128: the first frob ticket start/evidence invocation run from inside a git linked worktree resolved the repo root to the MAIN checkout (/home/logan/projects/frob) and wrote main's tickets.md, while later invocations in the same session correctly targeted the worktree. The same misresolution likely explains a mid-session incident where frob ticket close, run with cwd inside a worktree, transitioned the ticket in main's ledger. test_linked_worktree_resolves_to_worktree_root exists and passes, so the failure is conditional -- suspect cache/state (.frob dir presence?) or cwd-vs-env resolution order on first run. Repro attempt: fresh worktree, no .frob, run frob ticket show from the worktree root and compare the 'loaded N tickets under <path>' line. Fix the resolution order and add a regression test covering the first-invocation case.
## Done report

Non-repro with a mechanism: frob ticket root resolution is pure
cwd-based ((cfg.ticket_path or Path(".")).resolve()) with no git-aware
upward walk, so no code path can escape a linked worktree given a
correct cwd. Four repro variants (fresh worktree, .frob presence
permutations, diverged ledgers) all resolved correctly. The original
T-0128 incident is best explained by the agent harness resetting cwd
between shell calls, landing the first invocation on the main
checkout -- an operator-environment effect, not a frob defect.
Per the ticket's own instruction, four regression tests now lock the
correct behavior for every variant tried
(tests/system/test_cli_ticket_worktree_root.py). Verified at merge:
4/4 new tests plus 129 across the tickets/gitio suites.