---
id: T-4448
title: Post-land rapid sweep removes clean UNLANDED agent worktrees (t-4442, t-4446
  deleted while READY)
state: done
kind: bug
origin: agent
created: '2026-09-12'
priority: critical
parent: T-4410
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_release.py
- src/frob/tickets/_rapid_sweep*.py
- src/frob/verify/_sweep*.py
- tests/unit/test_rapid_sweep*.py
- src/frob/tickets/_worktree_sweep.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/rapid_sweep_suite/*.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_worktree_sweep.py
  reason: attempt 1 found the disposal verdict lives in _worktree_sweep.py (_sweep_verdict_for_worktree,
    _kept_* gates, remove_worktree) called from app/ticket_runner/_rapid_sweep.py;
    the declared globs matched no files
  actor: logan
  at: '2026-09-13'
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: attempt 1 found the disposal verdict lives in _worktree_sweep.py (_sweep_verdict_for_worktree,
    _kept_* gates, remove_worktree) called from app/ticket_runner/_rapid_sweep.py;
    the declared globs matched no files
  actor: logan
  at: '2026-09-13'
- op: add
  glob: tests/unit/rapid_sweep_suite/*.py
  reason: attempt 1 found the disposal verdict lives in _worktree_sweep.py (_sweep_verdict_for_worktree,
    _kept_* gates, remove_worktree) called from app/ticket_runner/_rapid_sweep.py;
    the declared globs matched no files
  actor: logan
  at: '2026-09-13'
evidence:
- tests/unit/rapid_sweep_suite/test_worktrees.py::TestSweepWorktreesAheadOfMain::test_clean_worktree_one_commit_ahead_is_kept
- tests/unit/rapid_sweep_suite/test_worktrees.py::TestSweepWorktreesAheadOfMain::test_clean_worktree_zero_ahead_ticket_done_is_removed
- tests/unit/rapid_sweep_suite/test_worktrees.py::TestSweepWorktreesAheadOfMain::test_clean_worktree_ahead_survives_even_with_done_report
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-09-12 in .frob/rapid-sweep/T-4430-899a8b12b8e0.log: "rapid sweep: worktree /home/logan/projects/frob/.claude/worktrees/t-4446 -> removed" (and the same for t-4442, and t-4427 after its land). t-4442 and t-4446 were implementer worktrees with READY, committed, UNLANDED work (branches t-4442 and t-4446 each 3 commits ahead of main: fix + evidence + done-report), clean trees, waiting for the serial land chain. The post-land rapid sweep treats "clean and older than the age threshold" as "disposable" and runs git worktree remove on them; the branches survive, but every later `frob ticket land <id> --worktree <wt>` then fails with "not found in worktree store" (three lands lost this way today, ~5 min each, plus the killed retries), and an agent still working in a removed worktree loses its checkout under it. The unlanded-work-leak memory describes exactly this shape: a clean-but-unlanded branch is invisible to the sweep, which marks it removable. ACCEPTANCE: (1) the sweep never removes a worktree whose branch has commits not reachable from main (git rev-list --count main..<branch> > 0) or whose ticket is in-progress on main; (2) the sweep logs, per kept/removed worktree, the reason including the ahead-count and ticket state; (3) a unit test with a clean worktree 1 commit ahead asserts kept; (4) `frob ticket land --worktree <wt>` on a registered-but-missing worktree whose branch exists re-adds the worktree from the branch instead of failing. Sprint v0.531.0. See also T-4437 (leaked disposable worktrees: the opposite failure).