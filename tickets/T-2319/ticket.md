---
id: T-2319
title: 'frob quality test: path positional only resolves root, never scopes SELECTION
  to a subdirectory'
state: done
kind: feature
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/test_runner.py
- src/frob/_cli_parsers/_check.py
- src/frob/_cli_parsers/_misc.py
- docs/modules/testing.md
- tests/unit/test_app_test_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: T-2319's actual CLI wiring for the test path positional lives in _misc.py
    (_add_test_parser/_populate_test_args), not _check.py -- ticket's declared scope
    named the wrong file
  actor: logan
  at: '2026-08-17'
- op: add
  glob: docs/modules/testing.md
  reason: document new PATH-scoped selection behavior (_explicit_path_selection)
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/unit/test_app_test_runner.py
  reason: new evidence file for _explicit_path_selection/_selection_report path-scoping
  actor: logan
  at: '2026-08-17'
evidence:
- tests/unit/test_app_test_runner.py::TestExplicitPathSelection::test_none_when_path_unset
- tests/unit/test_app_test_runner.py::TestExplicitPathSelection::test_none_when_path_is_root_itself
- tests/unit/test_app_test_runner.py::TestExplicitPathSelection::test_relative_subdir_scopes_selection
- tests/unit/test_app_test_runner.py::TestExplicitPathSelection::test_path_outside_root_is_ignored
- tests/unit/test_app_test_runner.py::TestSelectionReportPathScoping::test_path_selection_routes_to_python_only
- tests/unit/test_app_test_runner.py::TestSelectionReportPathScoping::test_path_selection_honors_lang_filter
- tests/unit/test_app_test_runner.py::TestSelectionReportPathScoping::test_root_path_falls_back_to_all
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: cf1fa0f2eb5149e009715a7d31d775fa0c2ba43d
---
Split from T-2252. `frob quality test`'s `path` positional
(`cfg.test_path`, src/frob/app/test_runner.py `_resolve_test_root`) is
used ONLY to resolve the repo root to start from -- it does not scope
test SELECTION to that subdirectory. `--all` sets every runner's
selection to the whole-suite sentinel regardless of `path`. There is no
way today to reproduce `pytest tests/unit/ -q -n auto`'s subset semantics
(or tests/integration, tests/system) via `frob quality test` -- only
`--lang` (by language) and the touched-set diff selection exist, neither
of which is directory-based.

Needed before T-2244's `test-unit:`/`test-integration:`/`test-system:`
Makefile leaves can repoint cleanly: add directory/path-based test
SELECTION scoping to `frob quality test` (not just root resolution), so
a caller can express "run only tests/unit/" (or integration/system)
through the frob CLI the same way a bare `pytest tests/unit/` does today.