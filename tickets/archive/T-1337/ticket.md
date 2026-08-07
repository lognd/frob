---
id: T-1337
title: OPAQUE001 x3 in src/frob/app lazy-dispatch (importlib + __getattr__)
state: done
kind: security
origin: agent
created: '2026-07-31'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/**
- docs/modules/app.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_app_lazy_dispatch.py::TestResolveRunner::test_imports_only_the_requested_subcommands_module
- tests/unit/test_app_lazy_dispatch.py::TestResolveRunner::test_unknown_subcommand_returns_none
- tests/unit/test_app_lazy_exports.py::TestLazyRunnerRunAttrs::test_accessing_one_alias_does_not_import_the_others
- tests/unit/test_app_lazy_exports.py::TestLazyRunnerRunAttrs::test_unknown_attribute_still_raises_attribute_error
designated_repro_test: null
acceptance:
- text: given frob check, when gate:OPAQUE runs, then src/frob/app raises 0 OPAQUE001
    errors
  evidence:
  - tests/unit/test_app_lazy_dispatch.py::TestResolveRunner::test_imports_only_the_requested_subcommands_module
  - tests/unit/test_app_lazy_dispatch.py::TestResolveRunner::test_unknown_subcommand_returns_none
  - tests/unit/test_app_lazy_exports.py::TestLazyRunnerRunAttrs::test_accessing_one_alias_does_not_import_the_others
  - tests/unit/test_app_lazy_exports.py::TestLazyRunnerRunAttrs::test_unknown_attribute_still_raises_attribute_error
threat: elevation-of-privilege
component: app
---
gate:OPAQUE errors: app/__init__.py:116 and app/app.py:115 importlib.import_module, app/__init__.py:107 class __getattr__ interception. These are the deliberate lazy-subcommand-dispatch mechanism (T-1318 adjacent). Either resolve statically or record a reasoned frob:waive OPAQUE001 naming the bounded module-name domain and where it is validated.