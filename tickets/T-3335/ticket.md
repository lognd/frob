---
id: T-3335
title: 'scaffold-type parity: verify/fix REF001/OPAQUE001 across pyo3/pybind11/web-app/cpp
  types'
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
- src/frob/scaffold/data/types/**
- src/frob/scaffold/data/shared/**
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
Found while working T-3277 (which fixed python-tool's scaffold-then-check
findings: REF001/REF002 via `[[refs.entrypoint]]` in frob.toml.j2,
OPAQUE001 via logging.getLevelNamesMapping() in filter.py.j2).

THE SHADOWING TRAP (the interesting/dangerous half, not just "more work
needed"): most of python-family's shared templates live under
src/frob/scaffold/data/shared/python/**, but four project types each
carry their OWN frob.toml.j2 override that SHADOWS the shared one
entirely, byte for byte, at render time:

  src/frob/scaffold/data/types/python-tool/frob.toml.j2
  src/frob/scaffold/data/types/pyo3-library/frob.toml.j2
  src/frob/scaffold/data/types/pybind11-library/frob.toml.j2
  src/frob/scaffold/data/types/web-app/frob.toml.j2

T-3277 initially fixed ONLY shared/python/frob.toml.j2, re-rendered a
python-tool demo, and saw ZERO change -- no error, no exception, the
render just silently used the per-type override instead. This is a
one-way trap: a future fix to the shared file will look correct (renders
fine, no test failure if nothing exercises the shadowed type) while doing
nothing for every type with its own override. T-3277 caught it only
because it happened to be measuring the exact type (python-tool) that has
an override; python-library (no override) got the shared-file fix "for
free" and looked deceptively like broader coverage.

WHAT TO CHECK for each of pyo3-library/pybind11-library/web-app (T-3277
only verified/fixed python-tool):
  1. Does the SAME REF001/REF002 shape apply (README.md, uv.lock or
     equivalent lock, CI workflow files, scripts/bump_version.py,
     tests/conftest.py, the package __init__.py, invariants/.gitkeep)?
     Almost certainly yes for the files each type still shares from
     shared/python/**, but each type's frob.toml.j2 needs its OWN
     `[[refs.entrypoint]]` block -- copy-paste from python-tool's fix is
     NOT free; verify against each type's actual rendered file set
     first (pyo3/pybind11 add native build artifacts, web-app swaps the
     Python test runner for typescript/vitest entirely).
  2. Does OPAQUE001 apply -- these types share shared/python/logging/
     filter.py.j2 (already fixed by T-3277) so this one IS shared and
     should already be fixed for all four; confirm by rendering each and
     running the equivalent of python-tool's DX check.
  3. cpp-library/cpp-tool use shared/cpp/frob.toml.j2 (a different shared
     tree entirely, not touched by T-3277 at all) -- audit separately.

Suggested first step: build the equivalent of tests/system/
test_scaffold_dx.py's pipeline for cargo (pyo3-library), cmake/ctest
(cpp-library/cpp-tool), and npm/vitest (web-app) -- three genuinely
different toolchains, not a parametrization of the existing Python-
toolchain test. pybind11-library may fit the existing Python pipeline
(pytest-based per its frob.toml.j2 diff against python-tool) with a
build step added.
