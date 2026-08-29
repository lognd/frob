---
id: T-3330
title: python-library scaffold fails make check (distinct findings from T-3277)
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/scaffold/data/types/python-library/**
- src/frob/scaffold/data/shared/python/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-3277 (which fixes python-tool's scaffold-then-check
findings). Widening T-3277's tests/system/test_scaffold_dx.py to also
parametrize over python-library surfaced a DIFFERENT, larger set of
`make check` failures on a fresh python-library scaffold, independent of
T-3277's REF001/REF002/OPAQUE001 fixes (python-library already inherits
those since it shares src/frob/scaffold/data/shared/python/frob.toml.j2
with python-tool):

  gate:TEST  3 errors, 9 warnings -- TEST001 (src/demo/logging/logger.py::
             get_logger has no unit test), TEST003 (scripts/, src/demo/
             logging/ below min_integration=1), TEST005 (0% branch/line
             coverage on src/demo/logging/{filter,formatter,logger}.py --
             python-library's tests/unit/test_placeholder.py does not
             cover the shared logging/ package the way python-tool's
             tests/unit/test_logging.py does)
  gate:DOC   5 errors -- COV001-shaped: public symbols in src/demo/
             logging/* and scripts/bump_version.py with no frob:doc edge
  gate:REF   2 errors -- re-measure once the above is understood; may
             already be fixed by T-3277's frob.toml.j2 refs entries
             landing in shared/python (python-library has no per-type
             frob.toml.j2 override, so it inherits T-3277's fix) --
             confirm before assuming still-broken

ROOT CAUSE (to verify): python-library's tests/unit/ only contains a
placeholder test; it needs real unit tests for src/demo/logging/* (or
that package needs excluding from python-library's scaffold if a library
type has no business shipping the full app/logging/ boilerplate
python-tool ships).

python-tool is unaffected and green (T-3277's own deliverable test:
tests/system/test_scaffold_dx.py::test_python_toolchain_scaffold_passes_check_immediately[python-tool]).
