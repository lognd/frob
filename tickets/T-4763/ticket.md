---
id: T-4763
title: typani floor to 0.2.3 and python-tool demonstrates Result at the config file-IO
  boundary
state: in-progress
kind: feature
origin: human
created: '2026-09-19'
priority: high
parent: T-4757
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/scaffold/data/shared/python/pyproject.toml.j2
- src/frob/scaffold/data/types/python-tool/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/system/test_scaffold_dx.py::test_all_registered_types_render_without_error
designated_repro_test: null
acceptance:
- text: Given the rendered pyproject, when the typani floor is read, then it equals
    0.2.3, the latest published release recorded in this ticket
  evidence:
  - tests/system/test_scaffold_dx.py::test_all_registered_types_render_without_error
- text: Given the rendered python-tool config loader pointed at a nonexistent file,
    when it is called, then it returns an error value and no exception escapes
  evidence:
  - tests/system/test_scaffold_dx.py::test_all_registered_types_render_without_error
- text: Given the rendered python-tool, when typani's own lint is run over it, then
    it is clean
  evidence:
  - tests/system/test_scaffold_dx.py::test_all_registered_types_render_without_error
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
typani is a declared dependency of every python type and appears in ZERO
generated modules. The floor is also stale: the templates pin typani>=0.0.3,
which predates the API refs/typani.md documents, so a fresh project can
resolve a pre-0.1 typani whose API does not match the house style at all.

1. Raise the floor to the latest published release: typani 0.2.3 (read from
   the PyPI JSON API on 2026-09-19). Record that in the pyproject template.
2. Make python-tool DEMONSTRATE the style rather than only declare the
   dependency. The generated from_external is the natural site: today it
   opens and parses a TOML file with a bare with-statement and a direct
   tomllib load, with no error handling at all. It becomes one propagate-
   decorated function returning a Result, with a note attached for context,
   and the file-I/O boundary wrapped by typani's exception-catching helper,
   per refs/typani.md.
3. The generated tests cover both arms: the success path and the missing or
   malformed file path, asserting the error VALUE, not an exception.

Positive controls:
1. the rendered python-tool passes typani's own lint;
2. a test renders python-tool, points its config loader at a nonexistent
   path, and asserts an error variant is returned rather than an exception
   escaping;
3. a test asserts the pyproject floor string equals the recorded version, so
   a future bump is a deliberate edit and not drift.
