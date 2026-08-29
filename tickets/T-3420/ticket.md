---
id: T-3420
title: 'coverage-instrumented pytest deadlocks in its own SIGTERM handler and survives
  timeout: likely cause of the CI and macOS hangs'
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
A coverage-instrumented pytest run that receives SIGTERM can DEADLOCK inside
coverage's own signal handler and then ignore the termination entirely, hanging
until something sends SIGKILL. This is a strong candidate for the CI hangs
already reported on this repo, including the macOS one.

MEASURED 2026-08-29 on a QUIET box (load ~1, 21GB free, no other agents, no
concurrent frob checks) -- so this is NOT host contention.

    shard: tests/system, 447 tests, serial (-p no:xdist), coverage enabled
    wrapper: `timeout 540`
    observed: EXIT=124 WALL=836s

The wall time is the first tell: the process was sent SIGTERM at 540s and was
still alive 296 seconds later. faulthandler's dump shows why. Reading the stack
from the bottom up, coverage's SIGTERM handler appears TWICE in one stack:

    coverage/control.py:761  _on_sigterm
    coverage/control.py:753  _atexit
    coverage/control.py:732  stop
    coverage/collector.py:348 stop
    coverage/collector.py:358 pause
    coverage/control.py:761  _on_sigterm     <-- RE-ENTERED
    coverage/control.py:755  _atexit
    coverage/control.py:855  save
    coverage/control.py:935  get_data
    coverage/collector.py:500 flush_data
    coverage/collector.py:185 _clear_data
        with self.data_lock or contextlib.nullcontext():   <-- BLOCKED HERE

The mechanism: the first SIGTERM enters `_on_sigterm`, which begins the
atexit/stop/pause path and takes `data_lock`. A SECOND SIGTERM arrives while
that lock is held, re-enters `_on_sigterm` on the same thread, and blocks
acquiring the same non-reentrant lock. Classic signal-handler re-entrancy
deadlock. `timeout` sending a follow-up TERM, or any supervisor that retries
termination, is enough to trigger it.

Above the coverage frames the stack is ordinary frob work -- graph ingest ->
lang.parse_file -> _walk_python -> _canonical_tokens' recursive `walk`. Nothing
about that code is at fault; it is simply what was executing when the signal
landed. Do NOT go looking for a bug in _walk_python.

WHY THIS LIKELY EXPLAINS THE CI HANGS. The reported CI failures included
faulthandler dumps and a macOS job that hung rather than failed. CI runs under
coverage, and CI runners terminate jobs with SIGTERM before escalating. A job
that deadlocks in its own SIGTERM handler presents exactly as "hung, then killed
by the runner" with a faulthandler dump attached. This hypothesis is testable
and MUST be tested rather than assumed -- see below.

WHAT TO DO, in order. Do not skip to a workaround.
  1. REPRODUCE DELIBERATELY. Start a coverage-instrumented run, send one
     SIGTERM, then a second SIGTERM shortly after while the first handler is
     still running, and confirm the deadlock. If a single SIGTERM is sufficient
     on its own, that is a DIFFERENT and more serious finding -- say so.
  2. Establish whether this is a known upstream coverage.py issue and which
     versions are affected. Record the installed version. If it is fixed
     upstream, the answer may simply be a version floor, and that is a fine
     answer -- report it rather than building something.
  3. Only if it is not fixed upstream, decide the local mitigation. Options
     include not installing coverage's SIGTERM handler in our runs, or
     escalating straight to SIGKILL after a bounded grace period. Both have
     costs: the first loses coverage data on terminated runs, the second loses
     it too and can corrupt partial data files. State the tradeoff.

THE USER-FACING CONSEQUENCE, worth stating in the fix: this makes a timeout
UNRELIABLE AS A KILL. Every `timeout N` guarding a coverage run in this repo --
including the ones in the agent playbook and CI -- may return 124 while the
process keeps running and holding its resources. Any process-count or
load-based measurement taken after such a "timeout" is reading a box that still
has the supposedly-dead run on it.

MUST-FIRE FIXTURE:   a coverage run receiving repeated SIGTERM terminates
                     within a bounded time.
MUST-STAY-QUIET:     a normal coverage run still writes complete data.

ACCEPTANCE
- Deliberate reproduction, with the single-vs-double SIGTERM question answered.
- Upstream status and installed version recorded.
- If mitigated locally, the data-loss tradeoff stated explicitly.
- Both fixtures committed.
