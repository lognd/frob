---
id: T-0567
title: 'DEAD001 residual: _documented_srcs/_run_jobs in gates/__init__.py'
state: done
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestRunJobsTimingAttribution::test_cpu_bound_neighbor_does_not_inflate_a_cheap_jobs_timing
designated_repro_test: null
threat: null
component: null
---
T-0565 fixed the callgraph/const-extraction substrate bugs behind most DEAD001 false positives and triaged the remainder, but src/frob/gates/__init__.py::_documented_srcs (line ~1717) and ::_run_jobs (line ~6986) are out of scope this wave (a sibling agent owns gates/__init__.py). Triage needed: _documented_srcs looks like a genuinely-orphaned helper superseded by _resolved_documented_srcs (verify with grep, likely delete); _run_jobs' docstring references a caller ('_run_jobs used to time each job...') suggesting a similar superseded-helper pattern. Either delete (with a zero-reference grep) or add a correctly-placed frob:tests/frob:invariant directive above the symbol itself (not above a test function -- the DSL binds Edge.src to whatever the comment sits directly above, several of T-0565's residual findings turned out to be frob:tests directives misplaced above the TEST function instead of the SOURCE symbol).