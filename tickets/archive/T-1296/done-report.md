## Done report

Closed real, targeted branch-coverage gaps in 12 src/frob/strata modules
by extending their existing unit test files (never new assert-True
filler): _atomic.py, _breach.py, _distributed_txn.py, _design_load.py,
_access.py, _clock_ordering.py, _delivery_semantics.py, _retry.py,
_backpressure.py, _circuit_breaker.py, _fallback.py, _deploy.py.

Each module now measures 100% branch coverage standalone (verified via
`pytest --cov=<module> --cov-branch` against its own test file, before
and after) -- confirmed BEFORE writing any test that the specific
missing branch line/arm reported by coverage was genuinely unexercised,
never added a second happy-path assertion to an already-covered branch.

Targeted branches, by module:
- _atomic.py: `_join_saga_idempotency`'s empty-coordinator-ids early
  return (line 108, only reachable by calling the private helper
  directly, since every real caller already guards it);
  `evaluate_saga_contracts`'s `build_facts` error-propagation arm (140);
  `evaluate_atomic_contracts`'s saga-error short-circuit before fault
  injection generation (217).
- _breach.py: `Quantity.leq`'s `UnitMismatch` arm inside
  `_check_bound_leq_revoke` (128, via a dimension-mismatched
  detect/revoke pair); `_compute_blast_radii`'s `build_facts` error arm
  (173); `_compute_and_evaluate_breach_report`'s blast-radii error arm
  (285) and scenario-evaluation error arm (296).
- _distributed_txn.py: `_multi_service_writers`'s self-loop
  (`flow.src == flow.dst`) exclusion branch (167->166);
  `check_distributed_txn_obligations`'s `bind_code` error-propagation
  arm (288).
- _design_load.py: `_read_and_elaborate`'s `OSError`-on-read arm
  (189-191, via a chmod-0000 unreadable file) and its elaborate-failure
  arm (205-210, via a secret missing `revoke`); `unbound_constructs`'s
  zero-ids-for-a-kind case and the `edge.kind in bound` False arm for an
  edge of an uninteresting kind (279->278).
- _access.py: `node_access_declarations`'s non-`access=`-prefixed attr
  skip (`continue`, line 182).
- _clock_ordering.py: `check_clock_ordering_obligations`'s `bind_code`
  error-propagation arm (327).
- _delivery_semantics.py, _retry.py, _backpressure.py,
  _circuit_breaker.py, _fallback.py: each REL-family entrypoint's own
  `bind_code` error-propagation arm, same pattern as
  `_distributed_txn.py`/`_clock_ordering.py`.
- _deploy.py: `_evaluate_generated_scenarios`'s `evaluate_scenarios`
  error-propagation arm (212).

All new/changed branches verified via monkeypatched collaborator
functions (`build_facts`, `bind_code`, `evaluate_scenarios`) returning
`Err`, or via real inputs that naturally drive the error path
(dimension-mismatched Quantity, unreadable file, malformed secret,
self-loop flow, non-access attr) -- never a mock that bypasses real
behavior verification of the surrounding function.

The ticket's one 0.0%-branch symbol, `_selfconform.py::
check_self_conformance`, was investigated per the brief's instruction:
it already has 67 real, frob:tests-bound assertions in
tests/unit/strata/test_selfconform.py and measures 95% coverage
standalone -- its 0.0% in the ticket brief is a stale/attribution
artifact (the T-1235/T-1395 tracked coverage-attribution defect the
coordinator separately flagged), not a real gap. No new test was added
for it and none was needed; it is not dead code (multiple live callers:
src/frob/gates/_sys.py, src/frob/strata/_native_test.py,
src/frob/app/sys_runner.py), so acceptance [1]'s dead-code-routing
branch does not apply either.

NOT DONE / LEFT OPEN: this covers only 12 of the ~35 root modules under
src/frob/strata. Acceptance [0] ("0 TEST005 findings under
src/frob/strata/**") is NOT met -- the remaining modules (_audit.py 88%,
_compliance.py 89%, _code_binding.py 91%, _crash.py 91%, _claims.py
54%, _elaborate.py 49%, and others not yet sampled) still carry real
partial-coverage gaps. Filed T-1415 ("TEST005 burn-down:
src/frob/strata remainder (post T-1296 partial)") to continue the same
per-module, per-branch discipline. Leaving T-1296 in-progress rather
than force-closing it against an acceptance criterion that is not
actually true, per the coordinator's explicit instruction on this
drive.

DISCLOSED CUT: the ticket's declared scope lists `tests/strata/**`,
which does not match this repo's real test tree
(`tests/unit/strata/**`) -- an ordinary scope-declaration typo. I could
not correct it: `frob ticket scope T-1296 --add
'tests/unit/strata/**'` (and even a single-file `--add`) fails with
`ScopeLeaseConflict` because T-1235 (a concurrent, in-progress,
unrelated ticket) holds a `tests/**` scope lease. This produces 12
SCOPE001 findings against `frob check --ticket T-1296` for the 12 real
test files this ticket touched -- all under the one real strata test
tree, none outside it. I did not force past this (no
`--allow-cross-ticket`, no hand-edit of tickets.md) since it is a real,
structural lease conflict, not a false positive to wave through. The
coordinator/reviewer can re-run `frob ticket scope T-1296 --add
'tests/unit/strata/**'` once T-1235 lands/releases its lease.

SELFAUDIT001 (7 findings, new test class names not yet declared in
design/frob.strata's testsuite interface) is the expected, known
land-time-absorbed drift per the playbook (`frob ticket land` runs its
own sync-interface step) -- not hand-fixed here.

`frob check --ticket T-1296` (repo-wide, per section 6c -- read
gate:scope-note before trusting any of this as ticket-scoped): 19
errors total = exactly the 12 SCOPE001 + 7 SELFAUDIT001 above, 0 other
new errors. `ruff check`/`ruff format --check`/`ty check` all clean
over every touched test file. All 128 tests across the 12 touched test
files pass in 0.43s (`pytest tests/unit/strata/test_atomic.py
tests/unit/strata/test_breach.py tests/unit/strata/test_distributed_txn.py
tests/unit/strata/test_design_load.py tests/unit/strata/test_access.py
tests/unit/strata/test_clock_ordering.py
tests/unit/strata/test_delivery_semantics.py tests/unit/strata/test_retry.py
tests/unit/strata/test_backpressure.py
tests/unit/strata/test_circuit_breaker.py tests/unit/strata/test_fallback.py
tests/unit/strata/test_deploy.py`).

`frob ticket land --dry-run` correctly refused to close T-1296: 3
acceptance criteria are still UNBOUND, matching the honest state above
(acceptance [2] is now bound to 5 of the 20 new node ids; [0] and [1]
remain unbound since they are not actually satisfied yet). Leaving the
ticket in-progress for the coordinator to either extend scope after
T-1235 lands, or split remaining work fully into T-1415 and
close this one as partially-superseded -- coordinator's call, not mine
to force.

### Changed
```
 tests/unit/strata/test_access.py             |  16 +++
 tests/unit/strata/test_atomic.py             |  93 ++++++++++++
 tests/unit/strata/test_backpressure.py       |  33 ++++-
 tests/unit/strata/test_breach.py             |  68 +++++++++
 tests/unit/strata/test_circuit_breaker.py    |  33 ++++-
 tests/unit/strata/test_clock_ordering.py     |  38 ++++-
 tests/unit/strata/test_delivery_semantics.py |  33 ++++-
 tests/unit/strata/test_deploy.py             |  35 +++++
 tests/unit/strata/test_design_load.py        |  82 ++++++++++-
 tests/unit/strata/test_distributed_txn.py    |  58 +++++++-
 tests/unit/strata/test_fallback.py           |  29 +++-
 tests/unit/strata/test_retry.py              |  38 ++++-
 tickets.md                                   | 202 ++++++++++++++++++++++++++-
 13 files changed, 748 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/unit/strata/test_atomic.py::TestJoinSagaIdempotencyNoCoordinators::test_empty_coordinator_ids_returns_model_unchanged` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_atomic.py::TestEvaluateSagaContractsFactsError::test_build_facts_error_is_propagated` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_atomic.py::TestEvaluateAtomicContractsSagaError::test_saga_error_short_circuits_before_fault_injection` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_breach.py::TestContainmentBounds::test_dimension_mismatched_bounds_fail_closed_with_unit_mismatch` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_breach.py::TestBreachContractsFactsAndScenarioErrors::test_build_facts_error_propagates_out_of_blast_radius` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_breach.py::TestBreachContractsFactsAndScenarioErrors::test_scenario_evaluation_error_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_distributed_txn.py::TestMultiServiceWritersSelfLoop::test_self_loop_flow_is_excluded_from_written_node_set` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_distributed_txn.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_design_load.py::TestLoadIds::test_unreadable_file_reported_as_parse_failed` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_design_load.py::TestLoadIds::test_elaborate_failure_reported_with_store_ids_and_resources_intact` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_design_load.py::TestUnbound::test_kind_with_zero_ids_contributes_nothing_and_outer_loop_continues` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_design_load.py::TestUnbound::test_edge_of_an_uninteresting_kind_is_skipped` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_access.py::TestNodeAccessDeclarations::test_non_access_attr_amid_access_attrs_is_skipped` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_clock_ordering.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_delivery_semantics.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_retry.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_backpressure.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_circuit_breaker.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_fallback.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_deploy.py::TestScenarioEvaluationErrorPropagation::test_evaluate_scenarios_error_propagates` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 20 passed (from 20 evidence id(s))
- gates: 0 error(s), 1966 warning(s), 699 waived
- error-findings: none (measured, zero errors)
