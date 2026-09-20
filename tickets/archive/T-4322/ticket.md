---
id: T-4322
title: Windows suite aborts on a worker controller error, so its failing set is unmeasured
state: done
kind: bug
origin: human
created: '2026-09-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_public_api_from_wheel.py
- tickets/T-4329/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tickets/T-4329/**
  reason: 'SCOPE001: bookkeeping shard for the T-4329 follow-up ticket filed while
    working T-4322 (out-of-scope OOM-crash root cause discovered here); the ticket''s
    own draft id does not yet match _TICKET_REF_RE''s 4-digit pattern so the standard
    cross-ticket commit-attribution exemption cannot fire until it is renumbered at
    land'
  actor: logan
  at: '2026-09-08'
body_changes:
- mode: append
  reason: 'BUG002: designated repro test cannot fail on this Linux host by construction
    (posix venv path is always correct here); the defect only manifests on win32'
  actor: logan
  at: '2026-09-08'
  old_length: 2844
  new_length: 3224
evidence:
- tests/system/test_public_api_from_wheel.py::test_advertised_public_api_imports_from_a_built_wheel
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE WINDOWS SUITE DOES NOT FAIL -- IT ABORTS, SO NO WINDOWS FAILURE COUNT ANYONE
HAS QUOTED IS A MEASUREMENT.

WHAT THE RUN ACTUALLY REPORTS, VERBATIM:

  SUITE-RESULT: DID-NOT-COMPLETE exitstatus=3 (INTERNAL-ERROR)
    collected=13726 (partial) failed=3 (partial, lower-bound)
    cause=KeyError: <WorkerController gw5>
  SUITE-RESULT: failing set INCOMPLETE -- run aborted before
    collecting/executing all tests, this is NOT the full failing set

A parallel worker controller raises and takes the whole session down. The suite
reports its own result honestly as partial and lower-bound, which is the one thing
working correctly here. Everything downstream of it is not: the backlog carries a
figure for how many Windows failures remain, and that figure cannot have been
derived from a completed run.

THIS IS A RECURRENCE, NOT A NEW CLASS. Two tickets already closed against exactly
this shape -- one for slow full-repo self-scan tests crashing parallel workers on
this platform and aborting the suite, one for raising the per-test timeout so
those same scans stop killing their worker. Both are done. The abort is back.
Establish whether the old fix regressed, was outgrown, or never covered the case
now firing, and say which; a third one-off timeout bump without that answer will
buy the same few weeks.

THE PARTIAL FAILING SET NAMES THE LIKELY CULPRITS and one of them is new. Two of
the three named tests are the full-repo self-model scans the earlier tickets were
about. The third builds real distribution artifacts and installs them into a
clean environment -- it was added only today, it is inherently slow, and it had
never run on this platform before. Check it first, and check whether it is
grouped with the other heavyweight tests the earlier fixes routed away from the
parallel workers, or whether it silently landed outside that grouping.

DO NOT FIX THIS BY RAISING A NUMBER UNTIL YOU KNOW WHAT THE NUMBER IS DOING. A
worker dying with a controller key error is not obviously the same event as a test
exceeding its own timeout, and treating them as interchangeable is how this
recurred. Get the actual crash cause from the run before choosing.

WHAT SUCCESS LOOKS LIKE HERE IS A COMPLETED RUN, NOT A GREEN ONE. The deliverable
is that the Windows suite executes to completion and emits a real, total failing
set. A completed run reporting thirty genuine failures is a success for this
ticket; the current state -- an unknown number -- is the defect. Say plainly what
the full failing set turns out to be so the remaining Windows work can finally be
scoped against a denominator.

NOTE ON PRIORITY: this platform is advisory in the workflow and does not block the
release, so do not let it displace release-blocking work. But it must not be
described as "advisory, some failures remain" while the true state is "unmeasured".

frob:waive BUG002 reason="Windows-only defect: venv_dir/bin/python only fails to exist on win32 (Scripts/python.exe there); on this Linux land host the posix path is always correct, so no test in the suite can fail at the parent commit to prove a genuine repro -- same posture T-3754s BUG002 waiver took for the identical class of Windows-runner-only crash with no Linux repro."