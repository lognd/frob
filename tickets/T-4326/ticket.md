---
id: T-4326
title: win32-only executable-resolution test fails on linux, the sole suite failure
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_gitio.py
- src/frob/gitio.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gitio.py
  reason: 'T-4326: the win32 test failure traces to a defect in _resolve_win32_executable
    itself (hardcoded os.sep/os.altsep instead of Windows'' two literal separators),
    not merely a missing test guard -- fixing it requires touching the production
    helper'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/gitio.py
  reason: 'T-4326: the win32 test failure traces to a defect in _resolve_win32_executable
    itself (hardcoded os.sep/os.altsep instead of Windows'' two literal separators),
    not merely a missing test guard -- fixing it requires touching the production
    helper'
  actor: logan
  at: '2026-09-08'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A WIN32-ONLY TEST FAILS ON LINUX, AND IT IS THE SINGLE FAILURE STANDING BETWEEN
THE LINUX LEG AND A GREEN SUITE.

MEASURED. The integration run's linux leg reports exactly one failing test out of
13,796 collected -- a test in the git-io suite covering the win32 executable
resolution added earlier today. It fails with an attribute error on a None object:
the platform-specific interface it reaches for does not exist off Windows, so the
lookup returns None and the attribute access raises.

WHY THIS SLIPPED THROUGH. The change was recovered from an abandoned worktree and
re-landed; its own suite was run and passed locally. Whatever guard keeps the
other tests in that group from running off-platform either does not cover this one
or is applied in a way that still evaluates the platform-specific expression. The
interesting question is not "add a skip" but why the sibling tests are safe and
this one is not -- answer that, because the same gap will bite the next test added
beside it.

FIX IT AT THE RIGHT LAYER. If the production helper is genuinely win32-only, the
test belongs behind the same platform guard its siblings use, applied so that the
platform-specific attribute is never touched during collection or setup on other
platforms. If instead the helper is meant to be callable everywhere and simply
no-op off Windows, then the DEFECT IS IN THE HELPER, not the test, and the test is
correctly reporting it -- decide which, and say so explicitly rather than reaching
for a skip by reflex.

DO NOT DELETE THE TEST. It covers real behaviour on the platform it targets, and
this project has measured that deleting or renaming a test silently orphans other
tickets' evidence.

VERIFY ON LINUX, which is where it fails, by running the whole git-io suite and
quoting the counts. If you conclude the right fix is a platform guard, also
confirm the test still RUNS and passes on Windows rather than being silently
skipped everywhere -- a test that never executes anywhere is worse than no test.
There is a `winrun` script available for measuring real Windows behaviour rather
than reasoning about it.
