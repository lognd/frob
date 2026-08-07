---
id: T-0574
title: 'agent environment hardening: auto-inject FROB_WORKTREE/FROB_AGENT + mechanical
  stash guard'
state: done
kind: security
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_worktree_guard.py
- src/frob/app/agent_runner.py
- src/frob/__main__.py
- src/frob/scaffold/_managed.py
- docs/guides/agent-playbook.md
- tests/test_worktree_guard.py
- README.md
- docs/modules/app.md
- tests/unit/test_scaffold_managed.py
- docs/commands/scaffold.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_worktree_guard.py
  reason: 'scope from the ticket''s own body: agent env subcommand, guard module,
    scaffold hook wiring, playbook doc, tests (was scope=[] and undispatchable)'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/app/agent_runner.py
  reason: 'scope from the ticket''s own body: agent env subcommand, guard module,
    scaffold hook wiring, playbook doc, tests (was scope=[] and undispatchable)'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/__main__.py
  reason: 'scope from the ticket''s own body: agent env subcommand, guard module,
    scaffold hook wiring, playbook doc, tests (was scope=[] and undispatchable)'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/scaffold/_managed.py
  reason: 'scope from the ticket''s own body: agent env subcommand, guard module,
    scaffold hook wiring, playbook doc, tests (was scope=[] and undispatchable)'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: docs/guides/agent-playbook.md
  reason: 'scope from the ticket''s own body: agent env subcommand, guard module,
    scaffold hook wiring, playbook doc, tests (was scope=[] and undispatchable)'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_worktree_guard.py
  reason: 'scope from the ticket''s own body: agent env subcommand, guard module,
    scaffold hook wiring, playbook doc, tests (was scope=[] and undispatchable)'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: README.md
  reason: 'DOC005: new subcommand needs its command-table row; docs are part of done'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: docs/modules/app.md
  reason: 'DOC005: new subcommand needs its command-table row; docs are part of done'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/test_scaffold_managed.py
  reason: 'R1: test_clean_after_apply''s block-count arithmetic must account for the
    new T-0574 stash-guard block'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: docs/commands/scaffold.md
  reason: 'M1: document the T-0574 stash-guard hook block alongside the other managed
    blocks'
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_worktree_guard.py::TestAgentEnvExports::test_resolves_worktree_root
- tests/test_worktree_guard.py::TestAgentEnvExports::test_non_repo_root_errs
- tests/test_worktree_guard.py::TestAgentRunnerEnv::test_env_prints_export_lines_for_worktree
- tests/test_worktree_guard.py::TestAgentRunnerEnv::test_env_defaults_to_cwd
- tests/test_worktree_guard.py::TestAgentRunnerEnv::test_env_non_repo_path_exits_nonzero
- tests/test_worktree_guard.py::TestStashGuardHook::test_refuses_stash_while_sibling_worktree_exists
- tests/test_worktree_guard.py::TestStashGuardHook::test_allows_stash_with_no_sibling_worktree
- tests/test_worktree_guard.py::TestStashGuardHook::test_commit_is_unaffected_by_the_hook
- tests/test_worktree_guard.py::TestStashGuardHook::test_idempotent_second_apply_is_noop
- tests/unit/test_scaffold_managed.py::TestStashGuardBlock::test_refuses_to_clobber_foreign_reference_transaction_hook
- tests/unit/test_scaffold_managed.py::TestStashGuardBlock::test_stale_ours_stash_guard_hook_is_updated
- tests/unit/test_scaffold_managed.py::TestScaffoldConformanceStatus::test_clean_after_apply
designated_repro_test: null
threat: null
component: null
---
Four agents ran git stash despite playbook 1b; several ran ticket commands against the shared checkout because FROB_WORKTREE was never SET (T-0431 guard exists but inert without it). (1) frob agent env prints/exports the guard env for a worktree; scaffold/playbook wire it into dispatch. (2) a pre-stash guard (hook or wrapper) refuses git stash while sibling agent worktrees exist. Catalogued-is-not-enforced applied to the playbook itself. Scope: src/frob/tickets/_worktree_guard.py, scaffold hooks, playbook.