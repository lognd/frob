+++
id = "01M2VFD1F2N2KQ4SBCNN3AD6CG"
title = "Wire 'frob scaffold unity-project <path>' into the scaffold CLI (scaffold_runner.py + CLI parser)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-19T00:00:00Z"
updated = "2026-09-19T00:00:02Z"
aliases = ["T-4578"]
scope = ["src/frob/app/scaffold_runner.py", "src/frob/_cli_parsers/_core.py", "src/frob/app/config.py", "src/frob/scaffold/_unity_project.py", "src/frob/app/_config_external.py", "docs/commands/scaffold.md"]
+++

T-4503 added render_unity_project(root, *, force=False) in src/frob/scaffold/_unity_project.py, a scaffold entry point whose signature (root only, no name/output_dir) does not fit render_project's uniform CLI dispatch. Wire a dedicated 'frob scaffold unity-project <path> [--force]' CLI form (or equivalent) calling it, per T-4503's own acceptance criterion 1 parenthetical ('or equivalent frob init detection'). Currently only reachable by importing the function directly (proven by tests/unit/test_scaffold_unity_project.py).
