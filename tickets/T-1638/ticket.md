---
id: T-1638
title: 'land resolves root from cwd: running it from inside a worktree targets the
  wrong repository'
state: queued
kind: bug
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/**
- src/frob/tickets/**
- tests/**
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
`frob ticket land <id> --worktree W` resolves its ROOT from the current working directory. Run it while cwd is inside W (or inside any other worktree), and the land treats that worktree as "main" -- merging into the wrong place, or refusing with a confusing error that names the wrong repository.

Hit twice on 2026-08-05 by the coordinator: a shell whose cwd had followed an earlier `cd` into a worktree launched two lands whose root was that worktree rather than the real main checkout. Both were caught only because they happened to refuse for an unrelated reason (DirtyMain in the wrong tree). A land that had proceeded would have merged a ticket into a sibling worktree's branch.

The same session also produced the mirror error at the git level: an `Edit` wrote to main's file by absolute path while the shell's cwd was inside a worktree, so the follow-up `git commit` targeted the worktree's branch instead of main. Recorded in the coordinator's own memory as a standing hazard, i.e. currently mitigated by discipline rather than by the tool.

Fix: `frob ticket land` must refuse when the resolved root is inside ANY registered worktree of the repository while `--worktree` names a different one. The check is cheap -- `git worktree list` is already parsed elsewhere in this codebase (`frob.tickets._leases._list_agent_worktrees`) -- and the refusal message should name both the resolved root and the intended target so the fix is obvious.

Consider the same guard for every other verb that takes `--worktree`, and for `--path`: a command whose target is derived from cwd is a foot-gun for any caller running from a shell with sticky cwd, which is every agent and every background job in this repo's workflow.

Regression test: from a cwd inside worktree A, `land <id> --worktree B` must refuse and name both roots.