---
id: T-1698
title: rapid land leaves root dirty via rapid-debt.jsonl, deadlocking every other
  agent's land
state: done
kind: bug
origin: agent
created: '2026-08-06'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/tickets/_land.py
- tests/unit/test_rapid_sweep.py
- docs/modules/tickets.md
- src/frob/tickets/_land_git_ops.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: porcelain_dirty_paths/describe_dirty_paths live beside _porcelain_dirty
    so the refusal message can never disagree with the rule that produced it
  actor: logan
  at: '2026-08-06'
- op: add
  glob: design/frob.strata
  reason: SYS100 capability declaration for the test module's git subprocess use,
    plus the SYS104 interface row for describe_root_dirt written by frob sys sync-interface
  actor: logan
  at: '2026-08-06'
evidence:
- tests/unit/test_rapid_sweep.py::TestCommitRapidDebt::test_leaves_the_repo_clean
- tests/unit/test_rapid_sweep.py::TestCommitRapidDebt::test_stages_only_the_debt_file
- tests/unit/test_rapid_sweep.py::TestDescribeRootDirt::test_names_a_real_dirty_file
- tests/unit/test_rapid_sweep.py::TestDescribeRootDirt::test_truncation_declares_itself
designated_repro_test: null
threat: null
component: null
---
Observed live 2026-08-06 with a three-agent wave: agent B landed T-1592,
and every subsequent land in the repo -- from any agent -- refused with
`DirtyMain: root checkout has uncommitted changes`. The whole fleet
deadlocked behind one file.

Cause. `record_rapid_debt` writes `rapid-debt.jsonl`, which is TRACKED by
design (its own docstring: the debt must survive a clone and a `frob
clean`, and must be reviewable in a diff). T-1684's
`spawn_deferred_post_land_sweep` calls it AFTER the land commit exists,
because the record names the commit it is deferring verification for.
Nothing then stages or commits that line, so the root checkout is left
permanently dirty, and `_check_dirty_main` -- correctly -- refuses the
next land.

This is the same class of problem `_write_release_bump` already solved
for pyproject.toml / CHANGELOG.md / .frob-release.json: a land-owned file
the land itself writes and must therefore stage into its own commit. The
rapid debt record was added without joining that discipline.

Note the write happens after the land commit is sealed, so it cannot join
that commit, and amending a commit is forbidden here. The fix is a small
dedicated follow-up commit made by the land itself:

    chore(rapid): record <ticket>'s deferred post-land sweep

Requirements:

- The land leaves the root checkout CLEAN in every rapid path, including
  the exec-disabled path (which records debt and then does not spawn).
- Best-effort: a commit failure must never fail a land that has already
  succeeded, but it must be logged at ERROR, because a silently dirty
  root deadlocks every other agent and the cause is invisible from the
  error they see.
- Idempotent and narrowly scoped: stage `rapid-debt.jsonl` ONLY, and only
  when it is actually dirty. Never `git add -A` on a shared root checkout
  that other agents' lands are racing against -- that would sweep up
  whatever another agent had in flight.
- Uses the land's own internal-commit channel so the T-0731 land-owned
  file hook is not fighting it.

Regression coverage must assert the ACTUAL invariant -- "root is clean
after a rapid land" -- rather than "a commit function was called".

Second, separable defect surfaced by the same incident: the error a
blocked agent sees (`DirtyMain: root checkout has uncommitted changes`)
does not name WHICH files are dirty. Three agents each burned several
minutes and one gave up without ever learning it was a single
one-line file. `_check_dirty_main` has the porcelain output in hand
already; it must name the paths (capped, with a count beyond the cap) in
the refusal. An error that does not name its own cause is a structural
defect in a tool whose entire job is enforcement.