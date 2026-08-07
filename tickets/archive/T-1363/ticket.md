---
id: T-1363
title: A failed coverage run must not overwrite a good stamp or ratchet floors down
state: done
kind: bug
origin: agent
created: '2026-07-31'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- Makefile
- src/frob/gates/_coverage.py
- frob-coverage.lock.json
- tests/test_gates.py
- tests/unit/test_makefile_coverage.py
- docs/modules/gates.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: T-1363 fix needs regression tests in test_gates.py/test_makefile_coverage.py
    plus a doc touch for write_coverage_lock's AFFECT001 closure
  actor: logan
  at: '2026-07-31'
- op: add
  glob: tests/unit/test_makefile_coverage.py
  reason: T-1363 fix needs regression tests in test_gates.py/test_makefile_coverage.py
    plus a doc touch for write_coverage_lock's AFFECT001 closure
  actor: logan
  at: '2026-07-31'
- op: add
  glob: docs/modules/gates.md
  reason: T-1363 fix needs regression tests in test_gates.py/test_makefile_coverage.py
    plus a doc touch for write_coverage_lock's AFFECT001 closure
  actor: logan
  at: '2026-07-31'
- op: add
  glob: design/frob.strata
  reason: T-1363 added a new test class needing a SYS104 testsuite interface declaration
  actor: logan
  at: '2026-07-31'
evidence:
- tests/unit/test_makefile_coverage.py::TestFailedRunNeverPromotesPartialData::test_failed_run_leaves_coverage_xml_and_stamp_untouched
- tests/unit/test_makefile_coverage.py::TestFailedRunNeverPromotesPartialData::test_successful_run_still_promotes_coverage_xml
- tests/test_gates.py::TestCoverageLoad::test_write_coverage_lock_refuses_downward_ratchet
- tests/test_gates.py::TestCoverageLoad::test_write_coverage_lock_allow_decrease_overrides_ratchet
designated_repro_test: null
acceptance:
- text: given a coverage run that exits nonzero, when it finishes, then the previous
    stamp and coverage.xml are left intact
  evidence:
  - tests/unit/test_makefile_coverage.py::TestFailedRunNeverPromotesPartialData::test_failed_run_leaves_coverage_xml_and_stamp_untouched
  - tests/unit/test_makefile_coverage.py::TestFailedRunNeverPromotesPartialData::test_successful_run_still_promotes_coverage_xml
- text: given a failed or partial run, when it finishes, then frob-coverage.lock.json
    is not rewritten downward
  evidence:
  - tests/test_gates.py::TestCoverageLoad::test_write_coverage_lock_refuses_downward_ratchet
  - tests/test_gates.py::TestCoverageLoad::test_write_coverage_lock_allow_decrease_overrides_ratchet
- text: given only a partial stamp exists, when a coverage-derived gate runs, then
    findings are disclosed as computed from partial data rather than reported as current
    fact
  evidence:
  - tests/unit/test_makefile_coverage.py::TestFailedRunNeverPromotesPartialData::test_failed_run_leaves_coverage_xml_and_stamp_untouched
threat: null
component: gates
---
Filed 2026-07-31. This is the defect that made the coverage situation WORSE rather than better, and it is a data-integrity bug, not a performance one.

WHAT HAPPENED: a `make coverage` run failed (MAKE_EXIT=2, six failing tests) and STILL OVERWROTE .frob/coverage-stamp and coverage.xml with the partial data it had collected. The four cross-agent validation symbols went from wrong-but-nonzero (6.7% / 11.1% / 20.0% / 0.0%) to uniformly 0.0%. The stamp after the failed run was strictly worse than the stamp before it, and nothing in the output said the data was untrustworthy -- the gate went right on computing TEST005 findings from it as current fact.

Of the six failures, only TWO were real regressions (SUPPRESS001 unregistered, suppress stage unrouted -- fixed at 4340f4ff). The other four pass in isolation and are parallel-load hermeticity flakes ("fatal: not a git repository", "cache.db ... database is locked") of the class T-1321 tracks. So the practical consequence is: ANY flaky test under load poisons the repo-wide coverage measurement for everyone, silently.

It also nearly corrupted a permanent artifact. `frob-coverage.lock.json` is TRACKED and holds coverage ratchet FLOORS. Both failed runs rewrote it downward (e.g. src/frob/app/__init__.py 76.5% -> 16.2%). Committing that would have permanently lowered the repo's quality floors using data from a failed run -- a silent strictness weakening arriving through a file nobody reviews. It was caught by hand twice today; it must not depend on that.

WHAT TO FIX (assess, do not assume):
1. A coverage run that fails MUST NOT overwrite a good stamp. Write to a temp path and promote only on success (the atomic temp+rename discipline T-1348 just added to the Tier-A fix engine is the same shape and the same reasoning).
2. If a partial stamp is genuinely worth keeping, it must be MARKED partial, and coverage-derived gates must refuse to report findings as current fact against it -- T-1205's acceptance [1] already specifies exactly this contract ("stale-and-disclosed rather than reported as current fact"). Prefer that over silent promotion.
3. `frob-coverage.lock.json` must never be rewritten by a failed or partial run at all. A ratchet floor may only ever be updated from a complete, passing measurement, and arguably should only ever move UP without an explicit override.
4. Consider whether a large single-run drop across many modules (e.g. dozens of modules dropping >20 points at once) should itself be treated as a degraded run and refused -- frob already does exactly this kind of self-defense elsewhere: during a land today it printed "10 frob:waive PERF008 directives went stale in one run (>= 5 threshold) -- treating as a degraded/under-reporting run, deleting nothing". That instinct is right and is missing here.

RELATIONSHIP TO NEIGHBOURS: T-1335 made a failing run LOUD (exit code propagates) -- necessary but not sufficient, since the bad data still lands. T-1353 fixed two real corruption sources (xdist oversubscription, thread-method timeout zombie). T-1205 makes refresh automatic and incremental. NONE of them stops a failed run from replacing good data with bad, which is this ticket.