---
id: T-2087
title: worker-crash signature regex may not match this repo's pinned pytest-xdist's
  real crash message
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/_coverage_refresh.py
- tests/test_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _coverage_refresh.py'
  actor: logan
  at: '2026-09-19'
  old_length: 3090
  new_length: 5696
evidence:
- tests/test_coverage.py::TestWorkerCrashSignatureRealSubprocess::test_summary_line_alone_matches_the_quoted_node_id
- tests/test_coverage.py::TestWorkerCrashSignatureRealSubprocess::test_os_exit_worker_crash_is_a_real_repro
- tests/test_coverage.py::TestWorkerCrashSignatureRealSubprocess::test_sigkill_worker_crash_is_a_real_repro
designated_repro_test: tests/test_coverage.py::TestWorkerCrashSignatureRealSubprocess::test_summary_line_alone_matches_the_quoted_node_id
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 72e21de29867ece6efb1be0be3b8d850a592d757
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

T-4718 sweep (condensed from src/frob/testing/_coverage_refresh.py:296-333,
trimmed for DOCARCH002's 12-line cap): the trimmed block's full original
text, kept verbatim below.

#: The xdist worker-crash signature this module knows how to detect and
#: retry serially (T-1672's "killed worker" incident, folded in here per
#: this ticket's own body: "fold T-1672 into this if one implementation
#: covers both"). `INTERNALERROR` is pytest's own marker for an
#: uncaught exception in its own machinery (xdist's scheduler raises
#: exactly this shape, `KeyError: <WorkerController gwNN>`, when a worker
#: process disappears out from under it, IF it happens); `gwNN` node-down
#: report lines are `execnet`'s. Matching any is enough to classify the
#: abort as an ENVIRONMENT failure (a worker got killed, most often OOM)
#: rather than a genuine test regression -- T-1672's item 3, "a resource
#: kill and a real suite failure both surface as exited 3; classify them
#: differently."
#:
#: T-2087: `worker\s+gw\d+\s+crashed` never actually matched on THIS
#: repo's pinned pytest-xdist (3.8.0) -- verified directly with both a
#: voluntary `os._exit` and a real `SIGKILL` inside a worker, run under
#: this repo's own installed xdist. The real summary line quotes the
#: node id (`worker 'gw1' crashed while running '...'`), which the old
#: pattern's bare `gw\d+` (no room for the surrounding `'...'`) could
#: never match. In practice this was masked rather than silent: every
#: reproduced crash shape ALSO printed `replacing crashed worker gwNN`
#: (the OTHER alternative here) earlier in the same output, so
#: `_pytest_outcome` still classified correctly end to end -- but the
#: summary-line branch existed to catch exactly the case where that
#: earlier line is NOT present in the captured output (e.g. a watchdog-
#: truncated capture, T-1677's own `_spawn_with_watchdog`), and in that
#: case it was silently dead. `'?` (both quote styles, and none, in one
#: pattern) fixes the summary-line branch without touching the other two.
#: The ORIGINAL `INTERNALERROR>...KeyError: <WorkerController gwNN>`
#: shape T-1672's own field incident recorded was NOT reproduced on this
#: pytest-xdist version despite both an `os._exit` and a `SIGKILL` repro
#: (see `TestWorkerCrashSignatureRealSubprocess` below) -- it may be
#: specific to an older xdist version this repo has since upgraded past;
#: the pattern is kept (matching it costs nothing and it may still occur
#: under a different failure timing this repro did not hit) but is no
#: longer the only, or even the primary, real-world match path.