---
id: T-4350
title: Tests invoke frob through the project runner inside fixture projects, 50 macOS
  failures
state: queued
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
- tests/test_app_daemon_proxy.py
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
THE MACOS CASCADE HAS MOVED FROM THE TOOL'S OWN SPAWNS TO THE TESTS' SPAWNS, AND
FIFTY FAILURES REMAIN.

MEASURED ACROSS THREE RUNS. The macos leg has gone 68 -> 61 -> 50 failures as two
successive fixes landed, and the underlying spawn error still appears 40 times. So
each fix was real and none reached the whole problem.

WHAT CHANGED, AND IT MATTERS. The earlier failures were the TOOL spawning a test
runner through the project runner. That was fixed by invoking the running
interpreter directly. The remaining failures are the TESTS spawning the tool:

  args=['uv', 'run', 'frob', 'graph', 'affects', 'helper.py::helper', '--json']
  Using CPython 3.14.7 interpreter at: /opt/homebrew/opt/python@3.14/bin/python3.14
  Creating virtual environment at: .venv
  warning: No `requires-python` value found in the workspace. Defaulting to `>=3.14`.
  error: Failed to spawn: `frob`
    Caused by: No such file or directory (os error 2)

Same shape, opposite direction. A test builds a temporary fixture project and
invokes the tool inside it through the project runner. That runner, finding a
project with no environment, creates an empty one on a default interpreter and
then cannot find the tool, because nothing was ever installed there.

WHY LINUX DOES NOT SHOW IT is already established and must not be re-derived: the
two legs resolve DIFFERENT versions of the project runner, because it was unpinned
and one leg hit a warm cache while the other downloaded a newer release whose
stricter environment check produced this behaviour. Pinning has since landed but is
not in the run being described here. So expect the linux leg to start failing the
same way once it resolves the same version -- this is not a macos bug and must not
be fixed as one.

THE FIX BELONGS AT THE TEST'S OWN INVOCATION. A test that wants to exercise the
tool inside a throwaway project should invoke the tool in a way that does not
depend on that project having an environment. The repository already adopted a
convention for exactly this problem on the tool's own side; look at what that
convention is and whether the test helpers can use the same one, rather than
inventing a second approach. If many call sites share a helper, fix the helper
once rather than each site.

COUNT THE CALL SITES FIRST AND SAY HOW MANY THERE ARE. Forty occurrences across
roughly six test files suggests a small number of shared helpers rather than forty
independent bugs. Establish that before changing anything; if it really is many
independent sites, that changes the shape of the fix.

DO NOT PAPER OVER IT BY SKIPPING THE TESTS ON THIS PLATFORM. They cover real
behaviour and the platform is not the problem -- the resolution mechanism is.

VERIFY honestly. If you cannot reach macos, say so and state plainly which
conclusions are inferred; do not present a linux run as evidence about a
macos-visible failure. Two tickets before this one were explicit about that
boundary and it is why the diagnosis kept improving instead of thrashing.
