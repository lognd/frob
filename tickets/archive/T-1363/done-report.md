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
