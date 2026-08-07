---
id: T-1508
title: z3-solver fails to build in worktrees, blocking dup._pipeline._smt TEST005
  burn-down
state: queued
kind: bug
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/dup/_pipeline/_smt.py
- tests/unit/test_dup_smt.py
- pyproject.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
src/frob/dup/_pipeline/_smt.py has TEST005 module-line coverage of 21.0%
(floor: 70%). Its own test file (tests/unit/test_dup_smt.py) correctly
skips when z3-solver is not importable -- but in this worktree,
`uv sync --extra smt` (the "frob[smt]" optional dependency group) fails
outright to build the z3-solver wheel:

  LibError: Unable to build Z3.
  hint: `z3-solver` (v5.0.0.0) was included because `frob[smt]`
  (v0.319.0) depends on `z3-solver`

This blocks raising this module's coverage from any worktree session
until the z3-solver build issue is resolved (likely needs a system
package -- cmake/a C++ toolchain matching what z3-solver's sdist build
expects -- or a prebuilt wheel pin). Filed while working T-1307 (TEST005
burn-down: src/frob/dup); T-1307's own scope was amended to exclude this
finding as environment-blocked rather than force it.

## Failure log
- 2026-08-05 attempt 1: z3-solver has no aarch64 linux wheel compatible with this glibc 2.35 host for any version, and sdist builds fail both directions: 5.0.0.0 needs a GCC with C++20 format header (absent in the system GCC 11.4), while 4.9.1.0 and earlier need CMake below 3.5 support (removed from the installed CMake 3.22); genuinely un-buildable in this worktree, not a pyproject fix