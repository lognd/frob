---
id: T-1532
title: WIRE001 text-scan misses bare-name-as-ProcessJob-argument wiring (job-table
  false positive)
state: done
kind: bug
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_wire.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestWireGate::test_new_function_passed_bare_to_process_job_constructor_is_not_flagged
- tests/test_gates.py::TestWireGate::test_new_function_never_passed_to_a_job_constructor_is_still_flagged
designated_repro_test: null
threat: null
component: null
---
WIRE001's _is_reached_outside_diff_tests (src/frob/gates/_wire.py) requires
a "ShortName(" call-shaped text occurrence to prove a diff-added symbol is
reached outside its own tests. A gate function registered into the process
job table as a bare first-class reference -- e.g.
"cache": _ProcessJob(cache_gate, (st.repo_root,)) in
src/frob/gates/__init__.py -- is genuinely wired (the job table invokes it)
but never appears text-adjacent to an opening paren under its own name, so
the scan reports it unreached. This is a distinct detector-gap shape from
T-1502 (memoize_per_run wrapper bare-name argument) and T-1527 (ErrorSet
no-paren member access): teach the scan to also recognize a bare short-name
appearing as a positional argument inside a _ProcessJob(...) (or similarly
shaped job-table constructor) call as a wired reference. Found while
landing T-1520 (CACHE001 static gate): cache_gate is wired via the "cache"
job-table entry but WIRE001 still flagged it.