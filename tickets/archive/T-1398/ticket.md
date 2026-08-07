---
id: T-1398
title: 'TEST005''s per-symbol join is broken: file coverage is good, symbols report
  0.0% -- most of the 2889 findings are artifacts'
state: dropped
kind: bug
origin: human
created: '2026-08-01'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN frob-coverage.lock.json records src/frob/__main__.py at 81.2 percent
    line coverage WHEN TEST005 evaluates __main__.py::main THEN it reports that symbol's
    real branch coverage, not 0.0 percent
  evidence: []
- text: GIVEN a successful unscoped make coverage run WHEN load_coverage reports module_join_fraction
    THEN it is above 0.95, or the shortfall is explained per unjoined module rather
    than silently deflating symbols to 0.0 percent
  evidence: []
threat: null
component: null
---
Measured on main 2026-08-01 from a clean, crash-free make coverage run (exit 0, 851 files stamped, source_sha=de76e283, .frob/last-coverage-run.log reached 100 percent with ZERO 'node down' occurrences).

frob-coverage.lock.json's module_line map holds good file-level data for the exact modules TEST005 calls 0.0 percent:

  src/frob/__main__.py            81.2   but TEST005: __main__.py::main = 0.0
  src/frob/serve/_socketd.py      65.1   but TEST005: daemon_version = 0.0
  src/frob/serve/_leases.py       40.3   but TEST005: ResourceLeaseManager.acquire/release/release_holder = 0.0
  src/frob/strata/_selfconform.py 79.6   but TEST005: check_self_conformance = 0.0

So collection works and file-level attribution works. What fails is the SYMBOL-level join -- mapping a file's coverage onto its individual functions/classes. load_coverage reports module_join_fraction=0.53, i.e. roughly half of mapped modules do not join; 306 symbols sit at exactly 0.0.

Three independent agents converged on this from different packages today, each having verified the code is genuinely well tested:
  - T-1279 (gates): 10 of the 12 symbols listed at 0.0 already had real, behavioral, frob:tests-bound tests covering both clean and finding-producing branches.
  - T-1296 (strata): _selfconform.py::check_self_conformance has 67 real assertions and measures 95 percent standalone.
  - T-1395 (attribution): proved __main__ and serve/ trace correctly under the subprocess rc in isolation, then failed the ticket rather than force a fix -- correctly, since the defect is not in the two files it scoped to.

WHY THIS IS CRITICAL, beyond the wrong number: the TEST005 count drives an entire burn-down program (T-1276, T-1279, T-1281, T-1294, T-1296, T-1305, T-1307, T-1309, T-1310, T-1350, T-1396 and more). Agents dispatched against a falsely-0.0 symbol find working tests already in place and are pushed toward writing filler tests against already-covered code to move a number that was never real. The gate is currently manufacturing busywork and disguising wherever the genuine gaps are.

Fix the join before any further TEST005 burn-down work is dispatched. T-1236's canary/deflation guard is the natural regression lock once the join is correct.

Supersedes the hypothesis in failed T-1395 (xdist worker-crash data loss): the measured run had no worker crash, so crash-loss does not explain it.

## Drop reason
- 2026-08-01: Premise disproven. The T-1398 agent generated a real coverage.xml and ran load_coverage/_test005_symbols directly against it: the per-symbol join in _coverage.py is correct, and acceptance [0] is already true today. I independently confirmed the same by reading the raw XML -- __main__.py shows 0/133 lines hit and _socketd.py 0/264, so TEST005 reporting 0.0% is faithful to the measured data, not a join failure. My filing was based on frob-coverage.lock.json, which turns out to disagree with the coverage.xml from the very run it records. That lock-vs-report inconsistency is the real defect and is now T-1401, which also carries forward T-1398 acceptance [1] (module_join_fraction=0.53, 447 of 851 modules absent from the report).