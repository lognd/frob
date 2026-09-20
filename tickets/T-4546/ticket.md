---
id: T-4546
title: 'flatten the remaining single-child verb groups: agent env, worktree sweep
  (in _core.py) and narrative move (frob/narrative/_cli.py + _root.py)'
state: done
kind: ux
origin: agent
created: '2026-09-16'
priority: low
parent: T-2994
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: v0.534.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_core.py
- src/frob/narrative/_cli.py
- src/frob/_cli_parsers/_root.py
- tests/unit/test_cli_single_child_groups.py
- src/frob/app/agent_runner.py
- src/frob/app/worktree_runner.py
- src/frob/__main__.py
- tests/test_worktree_guard.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/agent_runner.py
  reason: agent_runner.py owns frob agent's REAL runtime parser/dispatch (_build_agent_parser/run);
    _core.py's own _add_agent_parser is help-discovery only per its own docstring,
    so flattening the acceptance criterion's real bare-invocation behavior requires
    this file too
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/app/worktree_runner.py
  reason: worktree_runner.py owns frob worktree's REAL runtime parser/dispatch (sweep),
    same reason as agent_runner.py above
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/__main__.py
  reason: narrative move's positionals (file, line) collide with add_subparsers' own
    positional slot the same way agent's path positional did -- flattening 'frob narrative
    FILE LINE' requires normalizing argv before parse_args, and that boundary is owned
    by _dispatch_narrative in __main__.py, not by _cli.py
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/test_worktree_guard.py
  reason: T-1400's test_unrecognized_subcommand_falls_through_to_usage_error asserted
    bare 'frob agent' (no subcommand) exits 1 with a usage error -- exactly the behavior
    T-4546 intentionally flattens away (bare frob agent now runs env); the test needs
    updating to the new contract
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/test_worktree_guard.py
  reason: T-1400's test_unrecognized_subcommand_falls_through_to_usage_error asserted
    bare 'frob agent' (no subcommand) exits 1 with a usage error -- exactly the behavior
    T-4546 intentionally flattens away (bare frob agent now runs env); the test needs
    updating to the new contract
  actor: logan
  at: '2026-09-19'
evidence:
- tests/unit/test_cli_single_child_groups.py::TestAgentGroupFlattened::test_normalize_inserts_implied_env
- tests/unit/test_cli_single_child_groups.py::TestAgentGroupFlattened::test_bare_agent_defaults_to_env
- tests/unit/test_cli_single_child_groups.py::TestAgentGroupFlattened::test_run_dispatches_bare_invocation_to_env
- tests/unit/test_cli_single_child_groups.py::TestAgentGroupFlattened::test_help_notes_alias
- tests/unit/test_cli_single_child_groups.py::TestNarrativeGroupFlattened::test_normalize_inserts_implied_move
- tests/unit/test_cli_single_child_groups.py::TestNarrativeGroupFlattened::test_bare_narrative_defaults_to_move
- tests/unit/test_cli_single_child_groups.py::TestNarrativeGroupFlattened::test_help_notes_alias
- tests/test_worktree_guard.py::TestAgentRunnerEnv::test_bare_invocation_defaults_to_env
designated_repro_test: null
acceptance:
- text: GIVEN frob agent, frob worktree, frob narrative WHEN invoked without a subverb
    THEN each runs what its single child ran, the two-word spelling stays as a documented
    alias, and tests/unit/test_cli_single_child_groups.py covers all five groups
  evidence:
  - tests/unit/test_cli_single_child_groups.py::TestAgentGroupFlattened::test_normalize_inserts_implied_env
  - tests/unit/test_cli_single_child_groups.py::TestAgentGroupFlattened::test_bare_agent_defaults_to_env
  - tests/unit/test_cli_single_child_groups.py::TestAgentGroupFlattened::test_run_dispatches_bare_invocation_to_env
  - tests/unit/test_cli_single_child_groups.py::TestAgentGroupFlattened::test_help_notes_alias
  - tests/unit/test_cli_single_child_groups.py::TestNarrativeGroupFlattened::test_normalize_inserts_implied_move
  - tests/unit/test_cli_single_child_groups.py::TestNarrativeGroupFlattened::test_bare_narrative_defaults_to_move
  - tests/unit/test_cli_single_child_groups.py::TestNarrativeGroupFlattened::test_help_notes_alias
  - tests/test_worktree_guard.py::TestAgentRunnerEnv::test_bare_invocation_defaults_to_env
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-4522 flattened claude and natives; agent env and worktree sweep live in src/frob/_cli_parsers/_core.py (leased by T-4523 at the time) and narrative move's parser is src/frob/narrative/_cli.py wired from _root.py (leased by T-4520). Same mechanism as T-4522: default the dispatch dest to the single child and mirror the child's flags onto the group parser.

## Unblock log
- 2026-09-19: unblocked by T-3233 -- T-3233 landed on dev