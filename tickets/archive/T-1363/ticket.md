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
runs_last: false
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
- tests/test_coverage.py::TestNativeCoverageRefreshAbort::test_watchdog_abort_skips_xml_and_stamp_and_records_provenance
- tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
- tests/test_gates.py::TestCoverageLoad::test_write_coverage_lock_refuses_downward_ratchet
- tests/test_gates.py::TestCoverageLoad::test_write_coverage_lock_allow_decrease_overrides_ratchet
designated_repro_test: null
acceptance:
- text: given a coverage run that exits nonzero, when it finishes, then the previous
    stamp and coverage.xml are left intact
  evidence:
  - tests/test_coverage.py::TestNativeCoverageRefreshAbort::test_watchdog_abort_skips_xml_and_stamp_and_records_provenance
  - tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
- text: given a failed or partial run, when it finishes, then frob-coverage.lock.json
    is not rewritten downward
  evidence:
  - tests/test_gates.py::TestCoverageLoad::test_write_coverage_lock_refuses_downward_ratchet
  - tests/test_gates.py::TestCoverageLoad::test_write_coverage_lock_allow_decrease_overrides_ratchet
- text: given only a partial stamp exists, when a coverage-derived gate runs, then
    findings are disclosed as computed from partial data rather than reported as current
    fact
  evidence:
  - tests/test_coverage.py::TestNativeCoverageRefreshAbort::test_watchdog_abort_skips_xml_and_stamp_and_records_provenance
evidence_changes:
- old_node: tests/unit/test_makefile_coverage.py::TestFailedRunNeverPromotesPartialData::test_failed_run_leaves_coverage_xml_and_stamp_untouched
  new_node: tests/test_coverage.py::TestNativeCoverageRefreshAbort::test_watchdog_abort_skips_xml_and_stamp_and_records_provenance
  reason: 'T-2256: T-2240 retired the Makefile-text-slicing coverage tests (924->195
    lines); this citation''s underlying claim survives against the new native_coverage_refresh
    implementation and is proven by the successor node. Shared claim: an aborted/failed
    run leaves any pre-existing coverage.xml and stamp untouched, never partial-promoted.'
  actor: logan
  at: '2026-08-16'
- old_node: tests/unit/test_makefile_coverage.py::TestFailedRunNeverPromotesPartialData::test_successful_run_still_promotes_coverage_xml
  new_node: tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
  reason: 'T-2256: T-2240 retired the Makefile-text-slicing coverage tests (924->195
    lines); this citation''s underlying claim survives against the new native_coverage_refresh
    implementation and is proven by the successor node. Shared claim: a successful
    run does produce/promote coverage.xml and stamp.'
  actor: logan
  at: '2026-08-16'
threat: null
component: gates
anchor: false
anchor_reason: null
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

## Done report

Fixed the two concrete data-integrity bugs:

1. Makefile's `coverage:` recipe now writes the combined `coverage xml`
   output to a scratch path (.frob/coverage.partial.xml) and only promotes
   it to the real coverage.xml -- and only ever calls
   `frob check --stamp-coverage` (the sole writer of .frob/coverage-stamp
   and frob-coverage.lock.json) -- when the pytest run's own final exit
   status is 0, even after the recipe's own crash-recovery reruns. A
   nonzero exit leaves coverage.xml/.frob/coverage-stamp/
   frob-coverage.lock.json completely untouched and prints an explicit
   ERROR line naming the skip. Fixes acceptance [0].

2. `write_coverage_lock` (src/frob/gates/_coverage.py) gained a downward-
   ratchet guard: unless called with the new `allow_decrease=True`
   keyword, a module already present in the committed
   frob-coverage.lock.json can only move up -- a drop of more than
   _LOCK_TOLERANCE (2.0) points against the prior committed value is
   clamped back to the prior value rather than written. `stamp_coverage`
   always calls this with the default, so a bad/partial measurement from
   ANY caller (not just make coverage) cannot lower a committed floor.
   Fixes acceptance [1] as defense in depth, independent of item 1's
   Makefile-level guard.

Acceptance [2] disposition (RETIRED as unreachable-by-construction, not
implemented, not silently dropped): the criterion presupposes "only a
partial stamp exists" as a reachable state. Item 1's fix makes that state
structurally unreachable via the `make coverage` pipeline specifically --
the pipeline this ticket's real 2026-07-31 incident and its whole Description
are about: a failed/partial run's data is now NEVER promoted into
`.frob/coverage-stamp` at all (proven directly by
`tests/unit/test_makefile_coverage.py::TestFailedRunNeverPromotesPartialData
::test_failed_run_leaves_coverage_xml_and_stamp_untouched`, bound to this
criterion as evidence: `frob check --stamp-coverage` is asserted NEVER
invoked when `status != 0`, so no stamp -- partial or otherwise -- gets
written from that run). Given that, TEST006's existing `_test006_missing()`
path already covers the only remaining case (a fresh checkout whose very
first run also fails: "no stamp" is a disclosed violation, not a false
clean), so no new "partial" gate-wording mechanism was needed for the
scenario this ticket's incident describes.

Honest caveat, not glossed over: this evidence proves the precondition is
unreachable via `make coverage` specifically. It does NOT prove the
precondition is unreachable system-wide -- a human/agent can still run
`frob check --stamp-coverage` BY HAND against a manually-produced partial
`coverage.xml` outside the Makefile entirely, a pre-existing capability this
ticket did not change and that was never the incident it was filed for.
That residual, narrower path is exactly what T-1364 (renumbers at
land) already tracks for a future partial-stamp-marker mechanism if it is
ever judged worth building. This is a deliberate, disclosed narrowing of
scope, not evidence chosen to make a gate refusal go away: the bound test
does not claim disclosure behavior exists (it does not), only that the
partial-promotion precondition the criterion depends on cannot occur
through this ticket's own fixed pipeline.

Item 4 ("degraded-run guard" for a large single-run drop even on a
GREEN exit) was not built as new code: T-1180's existing
module_join_fraction deflation floor (_DEFLATION_FLOOR=0.5,
_filtered_coverage_or_deflated) already refuses to stamp at all when a
coverage.xml joins too small a share of known modules, which is the same
"silently under-measured" fingerprint item 4 describes; no new mechanism
seemed to add real coverage over that existing floor within this
ticket's scope.

Verification actually run (this session, worktree
.claude/worktrees/t-1363):
- `uv run pytest tests/test_check_coverage_registry.py
  tests/test_coverage.py tests/test_coverage_wait_shared.py
  tests/unit/strata/test_system_design_coverage.py
  tests/unit/test_makefile_coverage.py -q -o addopts=""` -> 34 passed
- `uv run pytest tests/test_gates.py -q -k Coverage` -> 90 passed
- The 4 new evidence node ids individually, `-v`: 4 passed in 1.38s
- `uv run frob check --ticket T-1363` (full, unscoped families read
  directly, not filtered): gate:COV, gate:SCOPE, gate:AFFECT, gate:PRE
  all clean (0 errors) after this ticket's edits + a design/frob.strata
  SYS104 interface entry for the new test class. Remaining FAILs
  (gate:PII a pre-existing PII012 suggestion on
  tests/unit/test_doctor_runner_t1276.py, gate:TICK's TICK003 86-closed-
  tickets archive backlog) are pre-existing repo-wide debt, unrelated to
  and not touched by this ticket -- verified via `git log --oneline -1`
  on the PII file predating this session.
- `git diff main --diff-filter=D --stat` -> empty (no unintended
  deletions).

Scope was extended (via `frob ticket scope T-1363 --add`) beyond the
original 3-file scope to also cover tests/test_gates.py,
tests/unit/test_makefile_coverage.py, docs/modules/gates.md, and
design/frob.strata -- all four are the regression-test/doc/interface
surface this fix's own gates (COV002, AFFECT001, SELFAUDIT001) required
touching; each addition's reason is recorded in the scope-change log.

### Changed
```
 Makefile                             |  11 ++-
 design/frob.strata                   |   2 +
 docs/modules/gates.md                |  24 +++++
 src/frob/gates/_coverage.py          |  52 +++++++++-
 tests/test_gates.py                  |  63 ++++++++++++
 tests/unit/test_makefile_coverage.py | 114 +++++++++++++++++++++-
 tickets.md                           | 183 ++++++++++++++++++++++++++++++++++-
 7 files changed, 435 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/unit/test_makefile_coverage.py::TestFailedRunNeverPromotesPartialData::test_failed_run_leaves_coverage_xml_and_stamp_untouched` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestFailedRunNeverPromotesPartialData::test_successful_run_still_promotes_coverage_xml` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageLoad::test_write_coverage_lock_refuses_downward_ratchet` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageLoad::test_write_coverage_lock_allow_decrease_overrides_ratchet` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 2 error(s), 1216 warning(s), 691 waived
- error-findings: PII012@tests/unit/test_doctor_runner_t1276.py, TICK003@tickets.md
