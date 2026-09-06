---
id: T-4107
title: 'the tests/ duplication floor never applies on Windows: two indexer sites emit
  a backslash rel that the prefix override table cannot match'
state: queued
kind: bug
origin: agent
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
- src/frob/dup/_legacy.py
- tests/unit/test_dup.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a short fixture-shaped duplicate under a tests directory, when find_duplicates
    runs with the default overrides, then it is retired by the floor on every platform
  evidence: []
- text: given a 20-plus-line genuine shared helper duplicated under tests, when find_duplicates
    runs, then it still registers as a group
  evidence: []
- text: given a fragment in a nested directory, when a CodeFragment is emitted, then
    its file field is forward-slash separated on every platform
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE `tests/` DUPLICATION FLOOR NEVER APPLIES ON WINDOWS, so every Windows run of
`frob dup` (and every gate that calls it) reports the short fixture-echo false
positives T-2970 was landed specifically to retire. Measured on the third
complete Windows CI run:

    tests/unit/test_dup.py::TestTestsDirectoryFloor
      ::test_short_fixture_style_duplicate_under_tests_is_no_longer_a_group

    Full diff:
    - []
    + [CloneGroup(clone_type='exact', size_lines=6, fragments=[
         CodeFragment(file='tests\\test_one.py', ...),
         CodeFragment(file='tests\\test_two.py', ...)])]

THE MECHANISM IS A TWO-LINE PATH-SHAPE BUG, and the failing output names it in
the `file=` field. In `src/frob/dup/_legacy.py`:

    line 145   the override table is a PREFIX table: (("tests/", 20),)
    line 157   matched with a bare `rel.startswith(prefix)`
    line 216   `rel = str(path.relative_to(root))`   <- python indexer
    line 247   `rel = str(path.relative_to(root))`   <- cpp indexer
    line 377   `rel = path.relative_to(root)` then `.as_posix()`  <- ALREADY RIGHT

`str()` of a relative path preserves the platform separator, so on Windows every
indexed fragment's `rel` is `tests\test_one.py`. `"tests\\test_one.py".
startswith("tests/")` is False, the floor is never raised, and the repo-wide
`min_lines=6` default applies under `tests/` exactly as it did before T-2970.

NOTE THE THIRD SITE AT LINE 377 ALREADY CALLS `.as_posix()` -- the file-walking
exclude path was fixed and the two indexer sites feeding the SAME `rel` into the
prefix table were not. A single module with one correct copy and two wrong copies
of the same conversion is the desync this repo exists to prevent; fix all three
to go through one place rather than adding a third spelling.

THIS IS THE SAME FAMILY AS T-3941/T-3947/T-3948 (a producer emitting a
platform-shaped rel that a downstream comparison assumes is POSIX) BUT NOT THE
SAME BUG, and the difference matters for the fix: those compare via
`is_excluded`/`is_test_file`, whose fnmatch happens to normcase and accidentally
match on Windows. This one compares with a bare `str.startswith`, which has no
such accident -- it simply fails, silently, every time. There is no
compensating error here, so the effect is fully realized on every Windows run.

WHAT THE FAILURE COSTS BEYOND THE ONE RED TEST, and why this is not test-only:
`find_duplicates` is called by the dup check, the prework gate, the arch gate,
and the dup runner (its own docstring at line 336 lists them). All four inherit
the default override table. So a Windows contributor sees duplication findings on
short test fixtures that a Linux contributor never sees, on the same tree -- and
the cheapest way to clear them is to churn or waive real test code. That is the
wrong-incentive shape.

WHAT TO DO
  1. Emit a POSIX `rel` at both indexer sites. Prefer routing all three through
     one helper so a fourth site cannot reintroduce the split.
  2. Decide whether `_effective_min_lines` should ALSO be defensive about its
     input shape. A prefix table matched by `startswith` is silently
     unsatisfiable against a wrongly-shaped key, with no error -- another
     silent-zero. Either normalize at the boundary or assert the shape; state
     which and why rather than doing both.
  3. Check for other bare-`startswith` prefix comparisons against a
     `relative_to`-derived path elsewhere in the tree. This one was found only
     because a test happened to cover it on Windows; a sibling with no Windows
     test would be invisible.

MUST-FIRE FIXTURE:   a short fixture-shaped duplicate under a tests directory is
                     retired by the floor when the fragment path is built the way
                     the indexers build it, on any platform.
MUST-STAY-QUIET:     the 20-plus-line genuine helper positive control already in
                     this class still fires -- the floor must not become a
                     blanket suppression.
THIRD FIXTURE:       a CodeFragment's `file` field is forward-slash separated
                     regardless of platform (a nested directory is required; a
                     bare filename has no separator to get wrong).

ACCEPTANCE
- Both indexer sites emit a POSIX rel, through one shared conversion.
- The Windows failure count drops by one and the existing positive control still
  passes.
- The `startswith`-against-a-derived-path question is decided explicitly.
- Any sibling bare-prefix comparison found is fixed or ticketed.
- All three fixtures committed.
