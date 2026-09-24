---
id: T-5482
title: 'Windows-only: full suite INTERRUPTED after test_ticket_verbs_wait errors --
  failing set is a lower bound'
state: queued
kind: bug
origin: agent
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: priority
  old_value: high
  new_value: medium
  reason: 'corrected: root cause is one unguarded ''import fcntl'' collection error,
    not a suite hang/timeout'
  actor: logan
  at: '2026-09-24'
body_changes:
- mode: append
  reason: 'investigated per coordinator request: root cause is a Windows-unguarded
    ''import fcntl'' collection error, not a suite hang/crash/timeout'
  actor: logan
  at: '2026-09-24'
  old_length: 1120
  new_length: 3416
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while draining CI run 35951365410 (dev 9e0c89bb19), windows-latest job
only -- URGENT, affects CI signal integrity: the whole pytest run was
INTERRUPTED (SUITE-RESULT: DID-NOT-COMPLETE exitstatus=2 (INTERRUPTED)
collected=15507 (partial) failed=1 (partial, lower-bound)) immediately
after tests/unit/test_ticket_verbs_wait.py errored:
SUITE-RESULT-FAILED: tests/unit/test_ticket_verbs_wait.py (error)

This means the windows-latest job's failing-test list (35 node ids
reported) is a LOWER BOUND, not the true failing set -- whatever test(s)
would have run after this point never got the chance to report, and any
of them could also be failing. tests/unit/test_ticket_verbs_wait.py
itself needs investigating first (its own collection/run error, not a
normal assertion failure) since it appears to be what triggered the
interruption -- possibly a hang that tripped the runner's own timeout/
kill mechanism, given the file name ("wait").

Until this is fixed, windows-latest CI results should be treated as
incomplete/unreliable for anything after this test in collection order,
not just for the 35 named failures.


CORRECTION after investigation (coordinator asked WHY the suite was
interrupted -- answer below): this is NOT a hang, worker crash, or
runner-level timeout. Re-reading the raw job log in full:

The MAIN pytest run (the one this drain's other windows tickets are all
drawn from) completed normally: SUITE-RESULT: exitstatus=1 collected=15507
failed=35 -- a real, COMPLETE result, not interrupted. Its one collection
error was tests/unit/test_ticket_verbs_wait.py failing to import:

  tests/unit/test_ticket_verbs_wait.py:19: in <module>
      import fcntl
  E   ModuleNotFoundError: No module named 'fcntl'

`fcntl` is POSIX-only and does not exist on Windows at all; this test
module imports it unconditionally at module scope instead of guarding it
platform-appropriately (contrast tests/unit/test_conftest_stackdump.py /
test_land_stackdump.py / test_stackdump.py in the SAME log, which SKIP
with "SIGUSR1 is POSIX-only" instead of failing collection -- the correct
pattern this file should follow, e.g. `pytest.importorskip("fcntl")` or a
`sys.platform` skipif before the import).

The "SUITE-RESULT: DID-NOT-COMPLETE (INTERRUPTED)" text that made this
look like a full-suite abort is from a SEPARATE, LATER event in the same
job log: `frob check`'s own COV003 gate independently re-runs `pytest
--collect-only` as a subprocess sanity check, and THAT collect-only
sub-run hits the exact same fcntl ImportError, fails collection ("!!!!!!!
Interrupted: 1 error during collection !!!!!!!" -- pytest's own standard
phrasing for ONE file's collection failing, not a suite hang), and its
own output happens to get logged right after a line that pattern-matches
this drain's SUITE-RESULT-line extraction regex, which is what
misattributed it as a second, later interruption of the MAIN test run.
There was no hang and no crash; both failures (this collection error in
the main run, and COV003's own re-detection of it) are exactly the one
root cause above.

Fix: guard `import fcntl` in tests/unit/test_ticket_verbs_wait.py the
same way the sibling POSIX-only test files already do (skip cleanly on
Windows instead of failing collection). Downgrading this ticket's
priority is reasonable once fixed -- filed at high priority originally
because it looked like a suite-wide interruption; it is not.
