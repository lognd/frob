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
evidence:
- tests/test_ticket_land.py::TestSiblingDoneReportPreserved::test_sibling_done_report_survives_landing_another_ticket
- tests/test_ticket_land.py::TestSiblingDoneReportPreserved::test_sibling_requeue_on_main_still_wins_when_neither_side_has_a_done_report
- tests/test_ticket_land.py::TestDraftFinalizeRewritesRegistryYamlRefs::test_registry_yaml_deferred_ref_rewritten_to_final_id
- tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_raw_merge_of_worktree_agent_branch_is_refused
- tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_raw_merge_override_env_var_allows_it
designated_repro_test: null
threat: null
component: null
---
All ~30 landings this session were manual: renumbering ~40 drafts (renumber does NOT rewrite registry yaml refs -- bit twice), reconciling 6 version-number collisions from parallel branches, states-regression sweeps. frob ticket land must own: draft finalization including reference rewrite across yaml/docs, version bump assigned AT LAND (serialized, no in-branch collisions), TICK005-backed regression sweep, push option. Then a hook refuses raw git merges of worktree-agent-* branches so land is the only path. Extends T-0338/T-0479. Scope: src/frob/tickets/_land.py, renumber, hooks, playbook.