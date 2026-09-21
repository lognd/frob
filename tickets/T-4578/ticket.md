---
id: T-4578
title: Wire 'frob scaffold unity-project <path>' into the scaffold CLI (scaffold_runner.py
  + CLI parser)
state: done
kind: feature
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/scaffold_runner.py
- src/frob/_cli_parsers/_core.py
- src/frob/app/config.py
- src/frob/scaffold/_unity_project.py
- src/frob/app/_config_external.py
- docs/commands/scaffold.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/scaffold/_unity_project.py
  reason: removing WIRE001 waiver now that a real CLI caller exists, per ticket body
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/app/_config_external.py
  reason: argparse Namespace -> AppConfig field-copy for scaffold_unity_root/scaffold_unity_force,
    the mapping layer _core.py/config.py alone cannot populate
  actor: logan
  at: '2026-09-19'
- op: add
  glob: docs/commands/scaffold.md
  reason: usage block + frob:doc anchor for the new unity-project CLI leaf
  actor: logan
  at: '2026-09-19'
evidence:
- tests/system/test_scaffold_unity_project_cli.py::TestScaffoldUnityProjectCli::test_success
- tests/system/test_scaffold_unity_project_cli.py::TestScaffoldUnityProjectCli::test_output_exists_refusal
- tests/system/test_scaffold_unity_project_cli.py::TestScaffoldUnityProjectCli::test_not_a_unity_project
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-4578
branch: t-4578
---
T-4503 added render_unity_project(root, *, force=False) in src/frob/scaffold/_unity_project.py, a scaffold entry point whose signature (root only, no name/output_dir) does not fit render_project's uniform CLI dispatch. Wire a dedicated 'frob scaffold unity-project <path> [--force]' CLI form (or equivalent) calling it, per T-4503's own acceptance criterion 1 parenthetical ('or equivalent frob init detection'). Currently only reachable by importing the function directly (proven by tests/unit/test_scaffold_unity_project.py).