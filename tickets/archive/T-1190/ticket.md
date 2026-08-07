---
id: T-1190
title: 'test: fix 5 unwaived TEST003/TEST014 findings found in T-0204 verification
  close'
state: dropped
kind: bug
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tomlio.py
- strata-core/src/parse/**
- src/frob/perf/_sampler.py
- src/frob/serve/_events.py
- src/frob/serve/_watch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-0204 verification close (2026-07-29) found gate:TEST is NOT honestly at
zero unwaived right now, despite T-0875's burn-down: 5 unwaived findings
exist (a 6th, TEST006 no-coverage-stamp, is an ordinary worktree artifact
of not having run `make coverage` here, not real debt):

- TEST003 src/frob/tomlio.py -- 0 integration test(s), below
  min_integration=1.
- TEST003 strata-core/src/parse -- 0 integration test(s), below
  min_integration=1.
- TEST014 src/frob/perf/_sampler.py::StackSampler.stop and
  src/frob/serve/_events.py::CoverageWatcher.stop share leaf name 'stop',
  both credited to the same convention-matched test -- ambiguous credit.
- TEST014 src/frob/perf/_sampler.py::StackSampler.stop and
  src/frob/serve/_watch.py::WatchThread.stop, same ambiguity.
- TEST014 src/frob/serve/_events.py::CoverageWatcher.stop and
  src/frob/serve/_watch.py::WatchThread.stop, same ambiguity.

These are new since T-0875 (not present in its own closing measurement)
-- new modules (tomlio, strata-core/parse, the perf/serve stop-method
trio) added afterward never got their own `frob:tests` edges. Add each
missing integration test (or a reasoned `frob:waive TEST003`), and
disambiguate the three TEST014 `stop` collisions with explicit
`frob:tests ... kind="unit"` edges naming which test actually exercises
each `.stop`, then re-verify `frob check --only gates-fast` shows 0
unwaived TEST findings again (TEST006 aside, which only ever clears via
`make coverage` at land, never in a worktree).

## Failure log
- 2026-07-29 attempt 1: T-0204's cited TEST003/TEST014 findings do not reproduce on current main: full frob check --ticket T-1190 shows gate:TEST at 0 errors, 6 warnings, 2 waived, none matching tomlio.py/strata-core-parse/perf-serve stop trio -- already resolved before this dispatch

## Drop reason
- 2026-07-29: not reproducible: the TEST003/TEST014 findings from T-0204's close-time measurement (taken under wave-22 landing concurrency) do not exist on current main -- verified by the w23-fixes agent via full foreground scoped checks (gate:TEST 0 errors) and direct reads of the cited modules' existing frob:tests edges; transient-measurement class