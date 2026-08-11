---
id: T-2087
title: worker-crash signature regex may not match this repo's pinned pytest-xdist's
  real crash message
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/testing/_coverage_refresh.py
- tests/test_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
## Problem

`_coverage_refresh.py`'s `_WORKER_CRASH_SIGNATURE_RE` (used by
`_pytest_outcome` to decide whether a non-zero pytest exit is an
environment crash worth a serial retry, vs. an ordinary red suite) is:

    _WORKER_CRASH_SIGNATURE_RE = re.compile(
        r"INTERNALERROR>.*WorkerController|worker\s+gw\d+\s+crashed|"
        r"replacing crashed worker"
    )

Found while implementing T-2032's follow-up (the addopts-injection ticket):
neither an `os._exit(1)` nor a real `os.kill(os.getpid(), signal.SIGKILL)`
inside a test running under this repo's installed pytest-xdist produces
any of the three patterns this regex expects. The actual message on this
version is:

    [gw1] node down: Not properly terminated
    ...
    worker 'gw1' crashed while running 'test_crash.py::test_crash_worker'

`worker\s+gw\d+\s+crashed` requires the literal token `gw<N>` immediately
after `worker` and whitespace -- the real message quotes it (`worker
'gw1' crashed`), so the regex does not match. Verified directly (2026-08-10):

    >>> import re
    >>> p = re.compile(r"INTERNALERROR>.*WorkerController|worker\s+gw\d+\s+crashed|replacing crashed worker")
    >>> bool(p.search("worker 'gw1' crashed while running 'test_crash.py::test_crash_worker'"))
    False

## Blast radius

If this regex genuinely cannot match a real crash on the pytest-xdist
version installed in this repo, T-1672/T-1677's whole worker-crash
detection-and-retry mechanism may never trigger automatically for a real
OOM kill either -- it would only ever have been exercised by the tests
that mock `_spawn`'s stdout with the OLD `INTERNALERROR>...
KeyError: <WorkerController gwNN>` string T-1672's original field
incident recorded, which may be a message shape an OLDER pytest-xdist
version produced and the currently-installed version no longer does.
This needs investigation before concluding the detection path is broken
in production, not just under a synthetic `os._exit`/`SIGKILL` repro --
a real OOM kill mid-run may still produce the original `INTERNALERROR>`
shape in some cases. Establish which shapes actually occur on this
repo's pinned pytest-xdist version before deciding the fix (widen the
regex vs. something else).

## Acceptance criteria

1. Determine (empirically, on this repo's pinned pytest-xdist version)
   every message shape a worker crash can actually produce -- at minimum
   a voluntary `os._exit`, a `SIGKILL`, and if feasible a real OOM
   (`ulimit`-constrained) -- and compare against `_WORKER_CRASH_SIGNATURE_RE`.
2. Fix or widen the regex so it matches what this repo's pytest-xdist
   version actually emits, with a test built from a REAL crashed-worker
   run (not a hand-typed string), matching the T-2032/T-2032-follow-up
   precedent of testing against real subprocess output rather than
   reasoning about it.
3. Report whether the ORIGINAL `INTERNALERROR>...KeyError:
   <WorkerController gwNN>` shape T-1672 was built from is still
   reachable at all on the current pytest-xdist version, or whether it
   was specific to an older version this repo has since upgraded past.
