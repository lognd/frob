---
id: T-4046
title: 'Windows: zoneinfo needs the tzdata package and nothing declares it, so even
  ZoneInfo(''UTC'') raises'
state: in-progress
kind: bug
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- pyproject.toml
- tests/unit/test_dependency_pins.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_dependency_pins.py
  reason: structural MUST-FIRE/MUST-STAY-QUIET coverage for the win32 tzdata marker
    lives in this shared dependency-pin test module
  actor: logan
  at: '2026-09-06'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED in the first COMPLETE Windows CI run (34024645783, commit 78f511af0):

    ModuleNotFoundError: No module named 'tzdata'
    zoneinfo._common.ZoneInfoNotFoundError: 'No time zone found with key UTC'

This is a PACKAGING GAP, not a code defect, and it is the cheapest Windows fix
available. Linux and macOS ship a system tz database that Python's `zoneinfo`
reads directly. WINDOWS DOES NOT. On Windows, `zoneinfo` requires the `tzdata`
PyPI package, and without it even `ZoneInfo("UTC")` -- the most basic possible
key -- raises.

So any code path reaching zoneinfo works on two platforms and cannot work on the
third, with no code difference between them. That is the portability-is-a-
property class: a dependency that is implicit on some platforms and explicit on
others, declared for none.

THE FIX is a platform-conditional dependency:

    tzdata; sys_platform == "win32"

VERIFY THE PLACEMENT rather than guessing which table it belongs in: this repo
declares runtime dependencies, optional extras, and a dev group, and the answer
depends on whether zoneinfo is reached by SHIPPED CODE or only by TESTS. Find the
actual import first. If shipped code reaches it, this is a runtime dependency and
CONSUMERS ON WINDOWS ARE ALSO BROKEN, which raises the priority well above "a CI
test fails". If only tests reach it, the dev group is right and the blast radius
is ours alone. STATE WHICH, with the import path that proves it.

NOTE THE HYPOTHESIS-TEST INTERACTION visible in the same log: the failure surfaced
through a hypothesis-generated example, with hypothesis reporting "These lines
were always and only run by failing examples: ...zoneinfo/__init__.py:24". So the
dependency is reached from generated data, which means the failure may be
intermittent across runs depending on what hypothesis generates -- do not treat a
passing run as evidence the dependency is unnecessary.

DO NOT fix this by skipping the affected tests on Windows. That would hide a
possible runtime gap for Windows consumers behind a test-only carve-out, which is
the wrong direction: the question "is shipped code broken on Windows" must be
answered, not sidestepped.

MUST-FIRE FIXTURE: importing the zoneinfo-dependent path on a Windows-shaped
environment without tzdata is a clear, named failure rather than a bare
ModuleNotFoundError deep in a test.
MUST-STAY-QUIET: Linux and macOS installs gain no unnecessary dependency --
the marker keeps it Windows-only.

ACCEPTANCE
- The import that reaches zoneinfo identified, and the runtime-vs-test question
  answered from it.
- tzdata declared with a sys_platform marker in the correct table.
- Whether Windows CONSUMERS are affected, stated explicitly either way.
- Both fixtures committed.