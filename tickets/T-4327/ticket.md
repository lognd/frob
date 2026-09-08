---
id: T-4327
title: macOS nested uv run ignores VIRTUAL_ENV and builds an empty fixture venv
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
- src/frob/testing/__init__.py
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
THE MACOS SPAWN CASCADE IS STILL LIVE AFTER ITS FIRST FIX, AND THE RUN NOW STATES
THE CAUSE OUTRIGHT INSTEAD OF LEAVING IT TO INFERENCE.

WHERE THINGS STAND, MEASURED ACROSS TWO RUNS. The macos leg went from 68 failing
tests to 61 after the first attempt, and the spawn failure itself still occurs 49
times in the log. So the first fix moved something but did not address the cause.
Its author correctly labelled the mechanism as inferred rather than verified,
having no access to the platform; this ticket has the measurement they lacked.

WHAT THE LOG NOW SAYS, and it is explicit:

  warning: `VIRTUAL_ENV=<repo>/.venv` does not match the project environment
    path `.venv` and will be ignored; use `--active` to target the active
    environment instead
  Using CPython 3.14.7 interpreter at: /opt/homebrew/opt/python@3.14/bin/python3.14
  Creating virtual environment at: .venv
  warning: No `requires-python` value found in the workspace. Defaulting to `>=3.14`.
  error: Failed to spawn: `pytest`
    Caused by: No such file or directory (os error 2)

READ THAT SEQUENCE CAREFULLY, because it inverts the previous diagnosis. The
environment variable IS now being set -- the first fix works as written. The
runner then DELIBERATELY IGNORES it, because the variable points at the outer
repository's environment while the nested command is being run against a
different project root (a temporary fixture directory). Having ignored it, the
runner creates a brand-new empty environment in the fixture directory, using a
default interpreter version because the fixture declares no requirement, and then
cannot find the test runner because nothing was ever installed into that new
environment. The cascade follows from there: collection fails, and every Python
evidence id resolves as unmeasured at once.

SO THE QUESTION IS NOT HOW TO MAKE THE VARIABLE STICK. It is what the nested
invocation should be doing when it runs a tool against a throwaway project that
has no environment of its own. The tool's own warning names one option outright.
Weigh it against the alternatives -- targeting the active environment explicitly,
not creating a fresh environment for these spawns at all, or invoking the tool
through the interpreter already running rather than through the project runner --
and choose deliberately rather than taking the first suggestion because it is
printed.

ESTABLISH WHY LINUX IS UNAFFECTED, because that difference is the real evidence
and it has not yet been explained. The same nested invocation runs there and
succeeds. Until you can say what differs, any fix is a guess that happens to
work; and this exact cascade has now survived one such guess.

WATCH FOR THE INTERPRETER VERSION. The log shows a fresh environment being built
on a much newer interpreter than the project targets, precisely because the
fixture declares no requirement. Even if the missing-runner error is fixed, a
fixture silently running under a different interpreter than the suite is a second
problem worth naming.

VERIFY AGAINST THE PLATFORM WHERE IT FAILS. If you cannot reach macos, say so and
state plainly which conclusions are inferred; do not present a linux run as
evidence about a macos-only failure. That honesty is what made the previous
attempt's limits visible, and it is why this ticket could be written.
