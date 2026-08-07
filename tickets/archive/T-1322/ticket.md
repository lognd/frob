---
id: T-1322
title: Investigate missing tests/test_check_runner.py relative to main (worktree deletion-filter
  hazard)
state: dropped
kind: bug
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_check_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Found while working the T-1289..T-1312 TEST005 cluster: `git diff main
--diff-filter=D --stat` in worktree .claude/worktrees/agent-a5aa94c3459b47f96
shows tests/test_check_runner.py (186 lines) deleted relative to main, with
NO deletion commit anywhere in this branch's own history and NO trace of
the file even in this worktree's earliest commit (predates this session's
first commit, e693cbed) -- it silently never made it into this branch at
all, despite existing on main (added at fa42ccf3, T-1261). This is the
exact deletion-filter hazard docs/guides/agent-playbook.md section 9 warns
about (a worktree created/merged against a base that structurally could
not carry forward another branch's file). Not caused by this session's own
commits (verified: `git show <first-commit-of-session>:tests/test_check_runner.py`
already fails). Needs investigation: diff the file's content on main
against what it should test, and either restore it via a clean merge/
cherry-pick or confirm its coverage is duplicated elsewhere before
concluding it is safe to drop.

## Drop reason
- 2026-07-29: False positive: tests/test_check_runner.py was born on main at fa42ccf3 (T-1261 land) after this branch's merge-base 97f02474; branch never touched it, 3-way land merge preserves it. Verified via git log --all -- tests/test_check_runner.py (single commit) and merge-base.