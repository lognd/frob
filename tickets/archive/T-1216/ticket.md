---
id: T-1216
title: 'perf: lazy per-subcommand runner import in frob.app -- drop eager deploy/strata/vet/gates
  import chain'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: high
parent: T-1204
tier: ticket
sprint: null
scope:
- src/frob/app/__init__.py
- src/frob/app/app.py
- tests/unit/test_app_lazy_exports.py
- tests/unit/test_app_lazy_dispatch.py
- docs/modules/app.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_app_lazy_exports.py
  reason: T-1216 adds two dedicated unit test files for the lazy __getattr__/resolve_runner
    behavior
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/unit/test_app_lazy_dispatch.py
  reason: T-1216 adds two dedicated unit test files for the lazy __getattr__/resolve_runner
    behavior
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/modules/app.md
  reason: T-1216 changes App's dispatch mechanism (_resolve_runner replaces _dispatch_table),
    doc anchor needs updating
  actor: logan
  at: '2026-07-29'
evidence:
- tests/unit/test_app_lazy_exports.py::TestLazyRunnerRunAttrs::test_accessing_one_alias_does_not_import_the_others
- tests/unit/test_app_lazy_exports.py::TestLazyRunnerRunAttrs::test_unknown_attribute_still_raises_attribute_error
- tests/unit/test_app_lazy_dispatch.py::TestResolveRunner::test_imports_only_the_requested_subcommands_module
- tests/unit/test_app_lazy_dispatch.py::TestResolveRunner::test_unknown_subcommand_returns_none
designated_repro_test: null
acceptance:
- text: GIVEN src/frob/app/__init__.py:14 imports every runner eagerly so 'frob ticket
    list' pays the deploy -> strata (417ms, incl strata._threat 280ms) -> vet._capability
    -> gates (213ms) import chain it never touches (775ms cumulative importtime, ~0.42s
    user on a quiet run) WHEN the package init dispatches subcommands via importlib/getattr
    lazily per app.py's own docstring THEN CLI invocations that do not touch deploy/strata/vet/gates
    save ~0.3-0.5s startup (report 'CLI startup' section)
  evidence:
  - tests/unit/test_app_lazy_exports.py::TestLazyRunnerRunAttrs::test_accessing_one_alias_does_not_import_the_others
  - tests/unit/test_app_lazy_exports.py::TestLazyRunnerRunAttrs::test_unknown_attribute_still_raises_attribute_error
  - tests/unit/test_app_lazy_dispatch.py::TestResolveRunner::test_imports_only_the_requested_subcommands_module
  - tests/unit/test_app_lazy_dispatch.py::TestResolveRunner::test_unknown_subcommand_returns_none
threat: null
component: null
---
Root cause: app/__init__.py:14 eagerly imports every runner; app.py's docstring already describes a dynamic importlib/getattr entrypoint that the package init does not follow. Fix: make __init__.py's dispatch table match app.py's documented lazy-import design so unrelated subcommands (e.g. ticket list) never pull in frob.deploy/frob.strata/frob.vet/frob.gates.