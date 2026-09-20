---
id: T-0577
title: 'land completion: auto-finalize drafts (with yaml ref rewrite), serialize version
  assignment, forbid raw ticket-branch merges'
state: done
kind: feature
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/**
- src/frob/app/ticket_runner.py
- docs/modules/tickets.md
- docs/guides/agent-playbook.md
- src/frob/scaffold/project.py
- tests/test_ticket_land.py
- tests/test_scaffold_worktree_lease_hook.py
- tests/system/test_cli_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/**
  reason: scope was empty at dispatch; landing draft yaml-ref rewrite, sibling-splice
    richer-state preservation, land-call serialization lock, raw-merge-forbidding
    pre-merge-commit hook
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/app/ticket_runner.py
  reason: scope was empty at dispatch; landing draft yaml-ref rewrite, sibling-splice
    richer-state preservation, land-call serialization lock, raw-merge-forbidding
    pre-merge-commit hook
  actor: logan
  at: '2026-07-22'
- op: add
  glob: docs/modules/tickets.md
  reason: scope was empty at dispatch; landing draft yaml-ref rewrite, sibling-splice
    richer-state preservation, land-call serialization lock, raw-merge-forbidding
    pre-merge-commit hook
  actor: logan
  at: '2026-07-22'
- op: add
  glob: docs/guides/agent-playbook.md
  reason: scope was empty at dispatch; landing draft yaml-ref rewrite, sibling-splice
    richer-state preservation, land-call serialization lock, raw-merge-forbidding
    pre-merge-commit hook
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/scaffold/project.py
  reason: scope was empty at dispatch; landing draft yaml-ref rewrite, sibling-splice
    richer-state preservation, land-call serialization lock, raw-merge-forbidding
    pre-merge-commit hook
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/test_ticket_land.py
  reason: scope was empty at dispatch; landing draft yaml-ref rewrite, sibling-splice
    richer-state preservation, land-call serialization lock, raw-merge-forbidding
    pre-merge-commit hook
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/test_scaffold_worktree_lease_hook.py
  reason: scope was empty at dispatch; landing draft yaml-ref rewrite, sibling-splice
    richer-state preservation, land-call serialization lock, raw-merge-forbidding
    pre-merge-commit hook
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/system/test_cli_ticket_land.py
  reason: scope was empty at dispatch; landing draft yaml-ref rewrite, sibling-splice
    richer-state preservation, land-call serialization lock, raw-merge-forbidding
    pre-merge-commit hook
  actor: logan
  at: '2026-07-22'
body_changes:
- mode: append
  reason: '_land_lock previously degraded to a documented no-op on a platform

    without fcntl (an unconditional, unbounded, logged-but-silent no-op --

    the same PLATFORM001-shaped bug T-2918 fixed elsewhere) instead of

    failing import. Fixed by delegating the platform branch to

    frob.process._lock''s shared portable_flock_acquire/portable_flock_release/

    lock_backend_available (T-3506) rather than re-deriving a fcntl/msvcrt

    pair in this module.'
  actor: logan
  at: '2026-09-19'
  old_length: 597
  new_length: 1002
- mode: append
  reason: 'Reusing _store._lock_path''s exact .frob/tickets.lock path for the land

    lock was tried first and broke: a worktree''s own tickets.lock (created

    the moment any ticket op runs there, then committed by land''s own

    git add -A wip-commit/finalize-commit steps) collides, by identical

    relative path, with the untracked lock file root''s own lock would have

    created -- git''s squash-merge refuses outright rather than silently

    picking a side. T-1619 later moved the path constant itself into

    frob.tickets._leases (LAND_LOCK_REL), the single home every other

    ledger-committing verb''s auto-commit choke point

    (_leases._add_and_commit_tickets_md) probes via

    refuse_if_land_in_progress before writing its own commit.'
  actor: logan
  at: '2026-09-19'
  old_length: 1002
  new_length: 1879
evidence:
- tests/ticket_land_suite/test_ledger_splice.py::TestSiblingDoneReportPreserved::test_sibling_done_report_survives_landing_another_ticket
- tests/ticket_land_suite/test_ledger_splice.py::TestSiblingDoneReportPreserved::test_sibling_requeue_on_main_still_wins_when_neither_side_has_a_done_report
- tests/ticket_land_suite/test_draft.py::TestDraftFinalizeRewritesRegistryYamlRefs::test_registry_yaml_deferred_ref_rewritten_to_final_id
- tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_raw_merge_of_worktree_agent_branch_is_refused
- tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_raw_merge_override_env_var_allows_it
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
All ~30 landings this session were manual: renumbering ~40 drafts (renumber does NOT rewrite registry yaml refs -- bit twice), reconciling 6 version-number collisions from parallel branches, states-regression sweeps. frob ticket land must own: draft finalization including reference rewrite across yaml/docs, version bump assigned AT LAND (serialized, no in-branch collisions), TICK005-backed regression sweep, push option. Then a hook refuses raw git merges of worktree-agent-* branches so land is the only path. Extends T-0338/T-0479. Scope: src/frob/tickets/_land.py, renumber, hooks, playbook.

<!-- narrative-moved:src/frob/tickets/_land.py:147:T-0577 -->
T-0577/T-2934/T-3506: same posix-only degradation as `frob.tickets.
_store`'s `ledger_lock` -- `_land_lock` used to degrade to a documented
no-op (an unconditional, unbounded, logged-but-silent no-op on a
platform without `fcntl`, the same PLATFORM001-shaped bug T-2918 fixed
elsewhere) rather than failing import. `_land_lock`'s own polling

<!-- narrative-moved:src/frob/tickets/_land.py:159:T-0577 -->
T-0577: dedicated lock file for serializing `land()` calls against the
SAME `root`, deliberately a DIFFERENT name from `_store._lock_path`'s
`.frob/tickets.lock`. Reusing that exact path was tried first and broke:
a worktree's own `.frob/tickets.lock` (created the moment ANY ticket
operation runs in the worktree, then committed into the branch by
`land`'s own `git add -A` wip-commit/finalize-commit steps) collides,
by identical relative path, with the untracked lock file `root`'s own
lock would have created -- git's squash-merge refuses outright ("would

T-1619: the path constant itself now lives in `frob.tickets._leases`
(`LAND_LOCK_REL`) -- that module is the single home every OTHER ledger-
committing verb's auto-commit choke point
(`_leases._add_and_commit_tickets_md`) probes via `refuse_if_land_in_