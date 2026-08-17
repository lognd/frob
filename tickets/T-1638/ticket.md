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
land_commit: null
---
`frob ticket land <id> --worktree W` resolves its ROOT from the current working directory. Run it while cwd is inside W (or inside any other worktree), and the land treats that worktree as "main" -- merging into the wrong place, or refusing with a confusing error that names the wrong repository.

Hit twice on 2026-08-05 by the coordinator: a shell whose cwd had followed an earlier `cd` into a worktree launched two lands whose root was that worktree rather than the real main checkout. Both were caught only because they happened to refuse for an unrelated reason (DirtyMain in the wrong tree). A land that had proceeded would have merged a ticket into a sibling worktree's branch.

The same session also produced the mirror error at the git level: an `Edit` wrote to main's file by absolute path while the shell's cwd was inside a worktree, so the follow-up `git commit` targeted the worktree's branch instead of main. Recorded in the coordinator's own memory as a standing hazard, i.e. currently mitigated by discipline rather than by the tool.

Fix: `frob ticket land` must refuse when the resolved root is inside ANY registered worktree of the repository while `--worktree` names a different one. The check is cheap -- `git worktree list` is already parsed elsewhere in this codebase (`frob.tickets._leases._list_agent_worktrees`) -- and the refusal message should name both the resolved root and the intended target so the fix is obvious.

Consider the same guard for every other verb that takes `--worktree`, and for `--path`: a command whose target is derived from cwd is a foot-gun for any caller running from a shell with sticky cwd, which is every agent and every background job in this repo's workflow.

Regression test: from a cwd inside worktree A, `land <id> --worktree B` must refuse and name both roots.

## Done report

Root cause confirmed as ticketed: `land()`'s existing T-1003 auto-resolve only
handles `root == worktree` (cwd sitting inside the SAME worktree being landed). The
dangerous shape T-1638 records -- cwd sitting inside a DIFFERENT worktree A while
landing ticket X from worktree B (`land <id> --worktree B` run with root defaulted
to A) -- was never caught: `root != worktree` trivially, so the T-1003 branch never
fires, and `root` (A, a linked worktree, not the primary checkout) is silently
treated as "main" for the whole land.

Fix: extended `_refuse_if_root_is_worktree` (src/frob/tickets/_land.py) with a
second check, after the existing root==worktree refusal: `_resolve_primary_checkout
(root)` (already used by `land()`'s own T-1003 logic) asks git's `--git-common-dir`
what root's TRUE primary checkout is. If that differs from `root` itself, `root` is
some other linked worktree, not the primary -- refuse (reusing
`LandError.IncompleteLand`, matching the existing convention for this guard family;
no new enum variant needed, and `_models.py` -- where `LandError` lives -- is
outside this ticket's declared scope). Unlike the T-1003 root==worktree case (where
auto-resolving is safe because the caller unambiguously forgot to cd out), a root
that is some THIRD worktree is genuinely ambiguous about intent, so this refuses
rather than silently guessing -- matching the ticket's own fix direction.

Both call sites of `_refuse_if_root_is_worktree` (`_land_precheck` for `land()`, and
`land_plan()`'s own preflight at line ~1054) get the new check for free -- no
per-caller change needed.

Changed:
- src/frob/tickets/_land.py::_refuse_if_root_is_worktree (extended)

Evidence:
- tests/unit/test_land_root_resolution.py::TestRootResolvesToADifferentWorktree.test_refuses_when_root_is_a_different_registered_worktree
  -- reproduces the exact incident shape (cwd inside worktree A landing worktree B's
  ticket); asserts the land refuses AND nothing mutated anywhere (neither the real
  primary checkout nor worktree A). Manually verified FAILS on pre-fix code (git
  apply -R of the fix's source-only diff, rerun: land went through clean, silently
  merging B's branch into A's own checked-out branch) and PASSES post-fix.
- tests/unit/test_land_root_resolution.py::TestRootResolvesToADifferentWorktree.test_root_equal_to_the_primary_checkout_is_unaffected
  -- sanity companion, the ordinary case (root IS the true primary checkout) still
  lands cleanly; the new check is a no-op there.
`--designate-repro --designate-repro-force` used on the first evidence id for the
same mechanical reason as T-1999: BUG002's automated re-run at the parent commit
returns NO_VERDICT (the test method did not exist at the parent commit, added in
the same commit as the fix), not because the repro is confirmatory-only -- the real
before/after behavior was verified directly above by reverting only the
source-code hunk via a saved patch and rerunning.

Also ran `tests/test_ticket_land.py -k "RootIsWorktree or ChainedCd"` (4/4 pass,
the existing T-0795/T-1003 root-resolution tests are unaffected) and the combined
`tests/unit/test_land_root_resolution.py tests/unit/test_land_cross_ticket_leakage.py`
suite (15/16 pass; the one failure, `test_queued_sibling_scope_overlap_does_not_
block`, is the same pre-existing flake already documented in T-1999's Done report,
unrelated to this change).

Filed: none new (this ticket needed no residue ticket).

Gates: `frob check --ticket T-1638` -- no SCOPE001/COV001/COV002/DOC00x/TEST001
finding against `src/frob/tickets/_land.py` or `tests/unit/test_land_root_
resolution.py` (the two files in this ticket's declared scope). Every FAIL in the
same run (gate:DOC repo-wide DOC006 backlog, gate:TEST TEST003/TEST014 repo-wide
findings, gate:SELFAUDIT SYS111 ratchet, gate:DSL CHANGELOG.md) is pre-existing and
outside this ticket's scope.

### Changed
```
 tickets/T-1638/ticket.md | 7 +++++--
 1 file changed, 5 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_land_root_resolution.py::TestRootResolvesToADifferentWorktree::test_refuses_when_root_is_a_different_registered_worktree` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_root_resolution.py::TestRootResolvesToADifferentWorktree::test_root_equal_to_the_primary_checkout_is_unaffected` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: DSL001@CHANGELOG.md, F401@/home/logan/projects/frob/.claude/worktrees/series-remainder/tests/unit/test_tickets_evidence_only_scope.py, SELFAUDIT001@design
