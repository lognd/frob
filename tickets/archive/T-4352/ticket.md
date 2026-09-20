---
id: T-4352
title: Type checker exits 2 with no diagnostics in macOS fixture projects, failing
  14 tests
state: dropped
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
- src/frob/process/parsers/ty.py
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
THE TYPE CHECKER EXITS NONZERO WITH NO DIAGNOSTICS INSIDE MACOS FIXTURE PROJECTS,
AND THAT ALONE FAILS FOURTEEN TESTS.

MEASURED, and this is a DIFFERENT cause from the spawn cascade that has been
chased through three tickets. These fourteen failures already invoke the tool the
correct way -- through the virtual environment's own interpreter, not through the
project runner -- so the spawn fix does not touch them. What they report is:

  ty: process exited 2 with no diagnostics reported
     (tool summary: 'linux: no issues; win32: no issues; darwin: no issues')

The check then exits 1 and the test asserting a clean fixture passes zero fails.

THAT MESSAGE IS ONLY LEGIBLE BECAUSE OF A FIX LANDED EARLIER TODAY. Before it, a
tool exiting nonzero with an empty diagnostic set was rendered as a plain FAIL
alongside a summary saying no issues on every platform -- a self-contradictory row
that would have sent a reader hunting a type error that does not exist. The
reporting is now honest; the underlying condition is what needs fixing.

ESTABLISH WHY IT EXITS 2 BEFORE CHANGING ANYTHING. Exit 2 with no diagnostics
means the checker did not complete a check, not that it found nothing. Candidates
worth distinguishing rather than guessing between: it cannot resolve the fixture
project's environment or interpreter; it is being invoked against a directory
whose layout it rejects; it fails on this platform for a reason unrelated to the
fixture; or it emits its complaint on a stream nobody is capturing. That last one
has ALREADY happened once today in this exact area -- a collection failure looked
silent purely because the error went to stdout while only stderr was read -- so
check the streams first, it is cheap and it was the answer last time.

DO NOT SUPPRESS THE TOOL TO GO GREEN. Skipping the type checker for fixture
projects, or treating a nonzero exit as a pass, would remove real coverage and
recreate the silent-failure shape this project has spent the day eliminating. If
the honest outcome is that the checker genuinely cannot run in this context, then
the right answer is that the check reports it as UNMEASURED -- vocabulary this
codebase already has -- rather than as either a pass or a failure.

ASK WHETHER LINUX IS GENUINELY UNAFFECTED OR MERELY LUCKY. A platform difference
in this repository has twice turned out to be a toolchain-version difference
rather than an operating-system one, and toolchain pins landed only after the run
being described here. Check whether the checker resolves the same version on both
legs before concluding this is macos-specific.

VERIFY on the platform where it reproduces. If you cannot reach macos, say so
plainly and state which conclusions are inferred; do not present a linux run as
evidence about a macos-visible failure.

## Failure log
- 2026-09-08 attempt 1: misdiagnosed: all 14 macOS failures are driven by ruff-check's hard tool_no_output_result error, not ty.py -- ty's silent-nonzero-exit already renders UNMEASURED and contributes 0 errors; real root cause filed as T-4354 (out of ty.py's scope, in _project_tool.py)

## Drop reason
- 2026-09-09: superseded: root cause was the macOS CI Test step never putting .venv/bin on PATH, fixed and landed as T-4368 (aab51604e)
