## Done report

New REL26x BACKPRESSURE-obligation family (`src/frob/strata/_backpressure.py`,
mirroring `_circuit_breaker.py`'s REL23x node-scoped structure): REL260
(missing bounded intake -- a `queue`/`consumer` node with no
`bounded_intake` attr) and REL261 (declared-but-unproven bounded intake,
proof-against-code via `_obligation_proof.py`'s shared owner-index/bound-
code/token-scan plumbing, no re-derivation). Both rules NODE-scoped,
single-instance-per-node (not registered in
`_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`, same carve-out REL230/REL231
use).

Wired into `src/frob/strata/__init__.py`'s public surface
(`check_backpressure_obligations`, `BackpressureReport`,
`BackpressureViolation`, `REL_MISSING_BOUNDED_INTAKE`,
`REL_UNPROVEN_BOUNDED_INTAKE`, `BACKPRESSURE_RULES`). NOT wired into
`frob.app.sys_runner` -- confirmed by inspection that
`check_retry_obligations`/`check_circuit_breaker_obligations`/
`check_fallback_obligations`/`check_spof` (T-0641/T-0642/T-0643/T-0645,
all already landed) are ALSO only exported from `strata/__init__.py` and
not yet wired into `sys_runner.py` either -- that CLI-wiring step is
evidently a separate follow-up across the whole REL2xx family, not
something this ticket alone left undone, and `src/frob/app/**` is outside
this ticket's declared scope regardless.

Added `docs/strata/reliability.md#rel26x-backpressure-obligation-t-0646`
(surface vocabulary, grammar-data ceiling disclosure, waiver channel),
following the REL22x/REL23x section template exactly.

Tests: `tests/unit/strata/test_backpressure.py`, 7 cases covering REL260
(queue node fires, consumer node fires, discharged/non-population clean,
waiver discharges) and REL261 (unproven fires, proven discharges,
no-bound-code is uncheckable not a violation) -- mirrors
`test_retry.py`'s real-tmp_path bind_code convention.

Measured:
- `uv run pytest tests/unit/strata/test_backpressure.py -p no:cacheprovider -q`
  -> 7 passed.
- `uv run frob check --only lint --ticket T-0646` -> PASS 0 errors 0 warnings.
- `uv run frob check --only static --ticket T-0646` -> PASS 0 errors (204
  warnings, all pre-existing/waived elsewhere in the tree; one frob-dup
  warning on this ticket's own test file, two near-identical Node-literal
  blocks across sibling test cases -- accepted as ordinary test-fixture
  repetition, not extracted).
- `uv run frob check --only gates-fast --ticket T-0646` -> PASS 0 errors
  (after a `frob ticket sweep T-0646` re-run to refresh PRE001 against the
  final file set).
- `uv run frob check --only gates-native --ticket T-0646` -> PASS 0 errors.
- `uv run frob check --only gates-security --ticket T-0646` -> PASS 0
  errors.

Cuts: none against the ticket's stated acceptance criterion (queue/
consumer node with no bounded-intake policy fires). CLI/`sys_runner`
wiring intentionally left out per the scope note above (matches the
existing landed sibling REL2xx families' actual state, not a regression).

### Changed
(no changed files detected)

### Evidence
- `tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake::test_queue_node_without_bounded_intake_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake::test_consumer_node_without_bounded_intake_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake::test_discharged_and_non_queue_nodes_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake::test_waiver_discharges_finding` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_backpressure.py::TestUnprovenBoundedIntake::test_declared_with_no_code_evidence_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_backpressure.py::TestUnprovenBoundedIntake::test_declared_with_real_code_evidence_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_backpressure.py::TestUnprovenBoundedIntake::test_declared_with_no_bound_code_is_uncheckable_not_a_violation` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 0 error(s), 2300 warning(s), 218 waived
- error-findings: none (measured, zero errors)
