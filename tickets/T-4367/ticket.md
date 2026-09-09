---
id: T-4367
title: Tool-absence classifier misses the tool-unavailable shape, failing on Windows
state: queued
kind: bug
origin: human
created: '2026-09-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/_python.py
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
A TEST ADDED YESTERDAY TO PROVE A MISSING TOOL IS REPORTED AS UNMEASURED FAILS ON
WINDOWS, BECAUSE ON WINDOWS THE ABSENCE ARRIVES IN A DIFFERENT SHAPE.

MEASURED on the windows leg, in the very test written to lock the new behaviour:

  tests/system/test_cli_check.py::TestCheckRuffAbsentFromTargetProject::
    test_missing_ruff_reports_unmeasured_not_error
  assert r.returncode == 0
  AssertionError: frob check <tmpdir>  [FAIL]  1 error  0 warnings
    ## Errors
      [ruff-check] tool unavailable: ruff -- install it or use make install-tool

THE FIX IT GUARDS IS CORRECT AND SHOULD NOT BE REVERTED. A chain of tickets
established that a tool absent from the target project is a legitimate
not-installed state and must be reported as UNMEASURED rather than as a hard
error, added a shared classifier for it, taught both parsers to use it, and wired
the evidence through to the real call site. That work eliminated the failure it
targeted on the platform where it was measured -- the "tool did not run" error
went from 32 occurrences to zero.

WHAT THIS SHOWS IS THAT THE CLASSIFIER RECOGNISES ONE SHAPE OF ABSENCE AND THERE
ARE AT LEAST TWO. The classifier matches the project runner's own spawn failure --
an exit code plus a "failed to spawn" message naming the tool. The message above
is different: it is this codebase's own "tool unavailable" path, reached before
any spawn is attempted. Same condition, different discovery route, and only one of
them is classified.

SO THE QUESTION IS WHERE ABSENCE SHOULD BE DECIDED. Two candidates, and they are
not equivalent: teach the classifier the second shape as well, which fixes this
instance and leaves a third shape possible; or find the one place that already
knows a tool is unavailable and route BOTH paths through the same decision, so the
answer cannot diverge by discovery route. This project has repeatedly paid for two
copies of one rule -- a liveness judgement, a stage-group membership list, a
citation scan -- and has repeatedly fixed it by making the second copy derive from
the first. Prefer that shape here unless you find a reason it does not fit.

CHECK WHETHER THE SAME SPLIT AFFECTS THE OTHER TOOL. The type checker travels the
same paths and was reconciled alongside the linter. If it has an equivalent
"unavailable" route, it has the same gap; say what you found either way.

DO NOT WEAKEN THE PRESERVED CASE. A tool that RAN and produced unparseable output
must still be a hard error -- that distinction was added deliberately after empty
output was being read as clean, and collapsing it would undo real protection.

VERIFY BOTH SHAPES AND BOTH DIRECTIONS: absent-via-spawn-failure and
absent-via-unavailable must each report unmeasured; present-but-broken must still
error. Windows is measurable locally with `winrun` (single shared mirror checkout;
venv uses `Scripts/` not `bin/`; bare `python3` hits a Store alias stub exiting
9009). An earlier ticket also reproduced this class on linux by restricting PATH
to a directory containing only the project runner, since the linter otherwise sits
beside it -- that technique works and is cheaper than a Windows round trip.
