---
id: T-1352
title: Bind INV-049 to clear the two INV006 errors T-1337 introduced in src/frob/app
state: done
kind: bug
origin: agent
created: '2026-07-31'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/app.py
- src/frob/app/__init__.py
- invariants/INV-049.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_app_lazy_exports.py::TestLazyRunnerRunAttrs::test_accessing_one_alias_does_not_import_the_others
- tests/unit/test_app_lazy_dispatch.py::TestResolveRunner::test_imports_only_the_requested_subcommands_module
designated_repro_test: null
acceptance:
- text: given an unscoped frob check, when gate:INV runs, then src/frob/app/app.py
    and src/frob/app/__init__.py raise 0 INV006 findings
  evidence:
  - tests/unit/test_app_lazy_exports.py::TestLazyRunnerRunAttrs::test_accessing_one_alias_does_not_import_the_others
  - tests/unit/test_app_lazy_dispatch.py::TestResolveRunner::test_imports_only_the_requested_subcommands_module
threat: null
component: app
---
T-1337's landed OPAQUE001 fix added docstrings to _import_runner_module / _import_runner_run_module asserting exclusivity (the closed if/elif import chains are the ONLY import path), with no frob:invariant edge anchored in either file. That is two live error-level INV006 findings on main.

The fix is already written and committed in the T-1276 worktree (commit 4d2c5001): a new invariants/INV-049.md bound to both files. It binds a REAL invariant rather than waiving, which is the correct disposition -- the closed-domain property is exactly the kind of claim this repo wants statically enforced instead of asserted in prose.

This is split out of T-1276 solely so it can LAND independently: T-1276's acceptance is a TEST005 count, which is unverifiable while the coverage stamp is broken (T-1335), so T-1276 must stay open -- but this invariant fix is coverage-independent and should not be held hostage to it.

WHY THIS REACHED MAIN: T-1337 verified with 'frob check --only opaque --ticket T-1337' -- filtered by gate AND by ticket scope -- so INV006 was invisible to it. Same false-green mechanism as the T-1293 incident, different gate. T-1351 is the guard.