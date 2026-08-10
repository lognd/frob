---
id: T-1638
title: 'land resolves root from cwd: running it from inside a worktree targets the
  wrong repository'
state: done
kind: bug
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- tests/unit/test_land_root_resolution.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land.py
  reason: 'probe: does T-1696''s stale lease file still block this path after its
    scope was narrowed'
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: src/frob/app/ticket_runner/**
  reason: 'Narrow to the files the recommended fix actually touches, and drop a

    probe path added while diagnosing a lease question.


    T-1638''s declared scope was four umbrella globs

    (src/frob/app/ticket_runner/**, src/frob/tickets/**, tests/**, docs/**).

    Starting it as scoped would lease essentially the whole codebase and

    serialize every other agent -- the same hazard TICK009 flags and that

    T-1664 was narrowed away from earlier today before it could block the

    queue.


    The investigation already done on this ticket (recorded by the

    land-attribution agent) identified the concrete fix: generalize the

    existing `if root == worktree: resolved_root = _resolve_primary_checkout(

    worktree)` block in `land()` so `root` is corrected via

    `_resolve_primary_checkout(root)` unconditionally, not only when it

    happens to equal --worktree. That is one function in one file, plus a

    regression test asserting SUCCESS (root silently corrected) rather than

    a refusal.


    Scope set accordingly. If implementation shows another file is genuinely

    required, `scope --add` it with a reason rather than pre-claiming

    umbrellas.

    '
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: src/frob/tickets/**
  reason: 'Narrow to the files the recommended fix actually touches, and drop a

    probe path added while diagnosing a lease question.


    T-1638''s declared scope was four umbrella globs

    (src/frob/app/ticket_runner/**, src/frob/tickets/**, tests/**, docs/**).

    Starting it as scoped would lease essentially the whole codebase and

    serialize every other agent -- the same hazard TICK009 flags and that

    T-1664 was narrowed away from earlier today before it could block the

    queue.


    The investigation already done on this ticket (recorded by the

    land-attribution agent) identified the concrete fix: generalize the

    existing `if root == worktree: resolved_root = _resolve_primary_checkout(

    worktree)` block in `land()` so `root` is corrected via

    `_resolve_primary_checkout(root)` unconditionally, not only when it

    happens to equal --worktree. That is one function in one file, plus a

    regression test asserting SUCCESS (root silently corrected) rather than

    a refusal.


    Scope set accordingly. If implementation shows another file is genuinely

    required, `scope --add` it with a reason rather than pre-claiming

    umbrellas.

    '
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: tests/**
  reason: 'Narrow to the files the recommended fix actually touches, and drop a

    probe path added while diagnosing a lease question.


    T-1638''s declared scope was four umbrella globs

    (src/frob/app/ticket_runner/**, src/frob/tickets/**, tests/**, docs/**).

    Starting it as scoped would lease essentially the whole codebase and

    serialize every other agent -- the same hazard TICK009 flags and that

    T-1664 was narrowed away from earlier today before it could block the

    queue.


    The investigation already done on this ticket (recorded by the

    land-attribution agent) identified the concrete fix: generalize the

    existing `if root == worktree: resolved_root = _resolve_primary_checkout(

    worktree)` block in `land()` so `root` is corrected via

    `_resolve_primary_checkout(root)` unconditionally, not only when it

    happens to equal --worktree. That is one function in one file, plus a

    regression test asserting SUCCESS (root silently corrected) rather than

    a refusal.


    Scope set accordingly. If implementation shows another file is genuinely

    required, `scope --add` it with a reason rather than pre-claiming

    umbrellas.

    '
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: docs/**
  reason: 'Narrow to the files the recommended fix actually touches, and drop a

    probe path added while diagnosing a lease question.


    T-1638''s declared scope was four umbrella globs

    (src/frob/app/ticket_runner/**, src/frob/tickets/**, tests/**, docs/**).

    Starting it as scoped would lease essentially the whole codebase and

    serialize every other agent -- the same hazard TICK009 flags and that

    T-1664 was narrowed away from earlier today before it could block the

    queue.


    The investigation already done on this ticket (recorded by the

    land-attribution agent) identified the concrete fix: generalize the

    existing `if root == worktree: resolved_root = _resolve_primary_checkout(

    worktree)` block in `land()` so `root` is corrected via

    `_resolve_primary_checkout(root)` unconditionally, not only when it

    happens to equal --worktree. That is one function in one file, plus a

    regression test asserting SUCCESS (root silently corrected) rather than

    a refusal.


    Scope set accordingly. If implementation shows another file is genuinely

    required, `scope --add` it with a reason rather than pre-claiming

    umbrellas.

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_land_root_resolution.py
  reason: 'Narrow to the files the recommended fix actually touches, and drop a

    probe path added while diagnosing a lease question.


    T-1638''s declared scope was four umbrella globs

    (src/frob/app/ticket_runner/**, src/frob/tickets/**, tests/**, docs/**).

    Starting it as scoped would lease essentially the whole codebase and

    serialize every other agent -- the same hazard TICK009 flags and that

    T-1664 was narrowed away from earlier today before it could block the

    queue.


    The investigation already done on this ticket (recorded by the

    land-attribution agent) identified the concrete fix: generalize the

    existing `if root == worktree: resolved_root = _resolve_primary_checkout(

    worktree)` block in `land()` so `root` is corrected via

    `_resolve_primary_checkout(root)` unconditionally, not only when it

    happens to equal --worktree. That is one function in one file, plus a

    regression test asserting SUCCESS (root silently corrected) rather than

    a refusal.


    Scope set accordingly. If implementation shows another file is genuinely

    required, `scope --add` it with a reason rather than pre-claiming

    umbrellas.

    '
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_land_root_resolution.py::TestRootResolvesToADifferentWorktree::test_refuses_when_root_is_a_different_registered_worktree
- tests/unit/test_land_root_resolution.py::TestRootResolvesToADifferentWorktree::test_root_equal_to_the_primary_checkout_is_unaffected
designated_repro_test: tests/unit/test_land_root_resolution.py::TestRootResolvesToADifferentWorktree::test_refuses_when_root_is_a_different_registered_worktree
threat: null
component: null
anchor: false
anchor_reason: null
---
`frob ticket land <id> --worktree W` resolves its ROOT from the current working directory. Run it while cwd is inside W (or inside any other worktree), and the land treats that worktree as "main" -- merging into the wrong place, or refusing with a confusing error that names the wrong repository.

Hit twice on 2026-08-05 by the coordinator: a shell whose cwd had followed an earlier `cd` into a worktree launched two lands whose root was that worktree rather than the real main checkout. Both were caught only because they happened to refuse for an unrelated reason (DirtyMain in the wrong tree). A land that had proceeded would have merged a ticket into a sibling worktree's branch.

The same session also produced the mirror error at the git level: an `Edit` wrote to main's file by absolute path while the shell's cwd was inside a worktree, so the follow-up `git commit` targeted the worktree's branch instead of main. Recorded in the coordinator's own memory as a standing hazard, i.e. currently mitigated by discipline rather than by the tool.

Fix: `frob ticket land` must refuse when the resolved root is inside ANY registered worktree of the repository while `--worktree` names a different one. The check is cheap -- `git worktree list` is already parsed elsewhere in this codebase (`frob.tickets._leases._list_agent_worktrees`) -- and the refusal message should name both the resolved root and the intended target so the fix is obvious.

Consider the same guard for every other verb that takes `--worktree`, and for `--path`: a command whose target is derived from cwd is a foot-gun for any caller running from a shell with sticky cwd, which is every agent and every background job in this repo's workflow.

Regression test: from a cwd inside worktree A, `land <id> --worktree B` must refuse and name both roots.