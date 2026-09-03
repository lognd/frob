---
id: T-3708
title: abandoned timeout worker threads block interpreter shutdown (win32 122s)
state: in-progress
kind: bug
origin: human
created: '2026-09-02'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/__init__.py
- src/frob/vet/_scan.py
- tests/test_lang.py
- tests/vet_suite/test_scan_tree.py
- src/frob/_daemon_timeout.py
- docs/modules/lang.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_lang.py
  reason: own the new shared daemon-thread timeout util and the T-3708 regression
    tests added to both call sites' test files
  actor: logan
  at: '2026-09-02'
- op: add
  glob: tests/vet_suite/test_scan_tree.py
  reason: own the new shared daemon-thread timeout util and the T-3708 regression
    tests added to both call sites' test files
  actor: logan
  at: '2026-09-02'
- op: add
  glob: src/frob/_daemon_timeout.py
  reason: own the new shared daemon-thread timeout util and the T-3708 regression
    tests added to both call sites' test files
  actor: logan
  at: '2026-09-02'
- op: add
  glob: docs/modules/lang.md
  reason: AFFECT001 requires touching this ticket's affects()-closure doc when _run_parse_with_timeout
    changes
  actor: logan
  at: '2026-09-02'
- op: add
  glob: design/frob.strata
  reason: SYS102/SYS003 require registering the new src/frob/_daemon_timeout.py module
    on the core node's code= glob (already-flowed-from by graphlang/vet/testsuite,
    zero new Flow declarations needed)
  actor: logan
  at: '2026-09-02'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Follow-up to T-3707/T-3692. frob.lang._run_parse_with_timeout and frob.vet._scan's _run_with_timeout each construct a fresh ThreadPoolExecutor(max_workers=1), submit fn, and on a timeout call executor.shutdown(wait=False) to abandon the still-running worker rather than block the caller past budget.

This does not actually free the interpreter from the worker: concurrent.futures.thread keeps a process-global weak registry of every worker thread any ThreadPoolExecutor has ever created, and its own atexit-registered _python_exit() unconditionally iterates that registry and joins every thread still alive at interpreter shutdown -- including ones a caller believes it abandoned via shutdown(wait=False). If the abandoned fn is genuinely still blocked when the process later tries to exit, interpreter shutdown hangs until that thread finishes (or forever).

This is the most likely real cause of the win32 CI ~120s post-check-pipeline gap (T-3692/T-3707): FROB_CHECK_TIMING breadcrumbs prove the check pipeline itself (including frob.gates' ProcessPoolExecutor, ruled out in T-3707) returns in ~1s, then something blocks interpreter shutdown for ~120s before the atexit-registered breadcrumb prints -- exactly the CPython concurrent.futures.thread global-join gotcha's signature.

Fix: replace the abandon-via-shutdown(wait=False) pattern in both call sites with a primitive that cannot block process exit -- e.g. spawn the worker as an explicit daemon=True threading.Thread (never registered with concurrent.futures.thread's global join registry) instead of a ThreadPoolExecutor, or otherwise ensure an abandoned worker cannot be joined at interpreter shutdown. Add a regression test for at least one of the two sites proving process exit is not blocked by a genuinely-hung abandoned worker (e.g. spawn one with a fn that sleeps far longer than the test, assert the test process/fixture completes promptly). Reference T-3707's Done report for the narrowing evidence.