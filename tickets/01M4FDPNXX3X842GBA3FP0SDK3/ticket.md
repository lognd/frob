+++
id = "01M4FDPNXX3X842GBA3FP0SDK3"
title = "frob test runs pytest from PATH instead of the project interpreter, and records a runner error as negative evidence; collection errors yield module symrefs as test ids"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-09T04:10:46Z"
updated = "2026-10-10T00:30:18Z"
labels = ["adoption:hullbreach"]
scope = ["changelog.d/**", "docs/reference/config.md", "docs/schemas/config.json", "docs/design/build-test-ci.md", "crates/frob-evidence/src/config.rs", "crates/frob-evidence/src/error.rs", "crates/frob-evidence/src/lib.rs", "crates/frob-evidence/src/provider.rs", "crates/frob-evidence/src/workspace.rs", "crates/frob-evidence/tests/evidence.rs", "crates/frob-tests/src/run.rs", "crates/frob-tests/src/verb.rs", "crates/frob-tests/tests/selection.rs"]

[[acceptance]]
text = "Given a Python project with a uv-managed .venv, when frob test runs, then pytest is invoked through the project interpreter (uv run or .venv/bin/python -m pytest) and --dry-run prints the resolved runner"
bound = true

[[acceptance]]
text = "Given pytest exits 2, 3 or 4 (interrupted, internal or usage/collection error), when frob test finishes, then no evidence is recorded, the outcome is Unresolved with reason runner-error and the collection error names the file path, never a module symref"
bound = true

[[acceptance]]
text = "Given a uv workspace whose packages are not importable by a PATH pytest, when frob test --base main runs, then pytest runs from the workspace .venv (or uv run) and a [tests] python knob can name the interpreter (logand.app-v2 F-543)"
bound = true
+++
