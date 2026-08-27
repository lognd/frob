---
id: T-3018
title: os.kill(pid,0) liveness probe can actually TerminateProcess on Windows (land.py,
  leases.py)
state: in-progress
kind: bug
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_leases.py
- src/frob/process/_pid_liveness.py
- src/frob/mutate/_journal.py
- docs/modules/process.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/process/_pid_liveness.py
  reason: extract shared frob.process._pid_liveness.pid_alive() so _land.py's identical
    unsafe os.kill(pid,0) probe and _journal.py's existing safe one share one implementation,
    per T-3018's own recommendation
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/mutate/_journal.py
  reason: extract shared frob.process._pid_liveness.pid_alive() so _land.py's identical
    unsafe os.kill(pid,0) probe and _journal.py's existing safe one share one implementation,
    per T-3018's own recommendation
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/process.md
  reason: frob:doc anchor for the new pid_alive() extraction
  actor: logan
  at: '2026-08-26'
triage_changes:
- field: priority
  old_value: medium
  new_value: high
  reason: 'spurious REF001/PRE001/SCOPE001 on any clean project directly undermines
    the standing transferability goal: every adopter sees false findings on first
    run, which is the give-up scenario frob status was built to prevent'
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`os.kill(pid, 0)` is used as a side-effect-free liveness probe in two more
places that were NOT in T-3003's scope to fix:

  src/frob/tickets/_land.py:614
  src/frob/tickets/_leases.py (probe around the T-1619 fcntl-degradation note)

T-3003 fixed the SAME pattern in src/frob/mutate/_journal.py::_pid_alive
after it caused a real Windows test failure
(tests/system/test_cli_doctor.py::TestDoctorMutateJournal::
test_run_diagnosis_unhealthy_with_stale_mutate_journal): CPython's Windows
`os.kill` opens the target process with PROCESS_ALL_ACCESS and calls
`TerminateProcess(handle, sig)` -- a `sig` of `0` still terminates
whatever process currently holds that pid with exit code 0. Combined with
Windows' fast PID reuse, a genuinely-dead pid probed shortly after exit
can be silently reassigned to an unrelated live process, and this
"probe" then actively kills it instead of merely observing it -- unlike
POSIX, where signal 0 is genuinely side-effect-free.

The mutate/_journal.py fix (T-3003) adds a Windows-only `_pid_alive_
windows` using `OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, ...)` +
`GetExitCodeProcess`/`STILL_ACTIVE` -- a query-only handle that cannot
terminate anything, dispatched via `sys.platform == "win32"`.

Recommend: extract a single shared `frob.process._pid_alive(pid) -> bool`
(or similar central home) that both `_land.py` and `_leases.py` (and
mutate/_journal.py) call, rather than three independent copies of the
same POSIX-only-safe pattern -- this is exactly the "no duplication"
class of defect: a fix applied to one copy and not the others leaves the
other two silently dangerous on Windows.

Not exercised by any currently-passing Windows CI test (the land/leases
probes are on a much less frequently hit path than the mutate-journal
doctor check that surfaced this), so it has NOT yet been observed
killing a live process on Windows CI -- but the mechanism is identical
and this should be fixed before Windows lands see meaningful production
traffic through frob ticket land / frob ticket work.

Filed while working T-3003; out of that ticket's declared scope
(src/frob/tickets/_land.py and _leases.py were not in scope).
