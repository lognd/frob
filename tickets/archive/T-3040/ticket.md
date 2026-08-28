---
id: T-3040
title: frob cycle refuses on bare tmp_path, breaking 3 test_system.py tests
state: done
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/mutate/
- tests/system/test_system.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/system/test_system.py::test_cycle_no_cycle_exits_zero
- tests/system/test_system.py::test_cycle_detects_cycle
- tests/system/test_system.py::test_cycle_suggest_flag
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 41b57e335b2dba8442f43078323a695c26e16680
---
Linux full-suite triage (T-2992): `frob cycle <dir>` refuses with exit 2
("could not resolve <dir> to a project root (no pyproject.toml and no git
repository found in any parent directory)") when pointed at a bare tmp_path
containing only a .py file -- but tests/system/test_system.py's three
`test_cycle_*` tests construct exactly that fixture (tmp_path with a
single `a.py`, no pyproject.toml, no git init) and assert `returncode == 0`.

Reproduced directly:
  python -m frob cycle /tmp/tmpXXXX
  -> WARNING: gitio: /tmp/tmpXXXX is not inside a git repository
  -> ERROR: frob cycle: could not resolve /tmp/tmpXXXX to a project root
     (no pyproject.toml and no git repository found in any parent
     directory) -- imports were NOT measured, this is not a clean report
  -> exit 2

Either `frob cycle`'s project-root resolution regressed to require a
pyproject.toml/git repo where it previously worked on a bare directory, or
the three tests below were always testing an assumption that stopped
holding and were never caught (macOS/prior CI runs may have historically
hung before reaching this point, per T-2980/T-2992's own discovery
context, so this could be long-standing and only now visible).

FAILING (3):
  tests/system/test_system.py::test_cycle_no_cycle_exits_zero
  tests/system/test_system.py::test_cycle_detects_cycle
  tests/system/test_system.py::test_cycle_suggest_flag

TRIAGE NEEDED: decide whether `frob cycle` should work on a bare
directory (fix the resolver / relax the requirement) or whether these
three tests should construct a real git repo or pyproject.toml fixture
(fix the tests) -- not decided here, filed for whichever owner has the
context on `frob cycle`'s intended contract.