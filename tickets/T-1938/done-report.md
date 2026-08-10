## Done report

Changed:
- src/frob/strata/_waive.py::stale_relwaive_violations (new, exported)
- src/frob/strata/_backpressure.py::check_backpressure_obligations
- src/frob/strata/_circuit_breaker.py::check_circuit_breaker_obligations
- src/frob/strata/_clock_ordering.py::check_clock_ordering_obligations
- src/frob/strata/_delivery_semantics.py::check_delivery_semantics_obligations
- src/frob/strata/_distributed_txn.py::check_distributed_txn_obligations
- src/frob/strata/_fallback.py::check_fallback_obligations
- src/frob/strata/_interactive_cost.py::check_interactive_cost_obligations
- src/frob/strata/_message_schema.py::check_message_schema_obligations
- src/frob/strata/_observability.py::check_observability_obligations
- src/frob/strata/_process_bounds.py::check_process_bounds_obligations
- src/frob/strata/_reliability.py::check_reliability_timeouts
- src/frob/strata/_reliability.py::check_reliability_health
- src/frob/strata/_retry.py::check_retry_obligations
- src/frob/strata/_shared_state.py::check_shared_state
- src/frob/strata/_slo.py::check_slo_obligations
- src/frob/strata/_spof.py::check_spof
- src/frob/strata/_ssot.py::check_ssot_obligations
- src/frob/strata/_starvation.py::check_starvation_obligations
- src/frob/strata/_supply_chain_boot.py::check_supply_chain_boot_obligations
- src/frob/strata/_sync_depth.py::check_sync_chain_depth
- src/frob/strata/_txn.py::check_txn_boundary_obligations
- docs/strata/reliability.md (T-1938 no-behavior-change note, satisfies AFFECT001 for all 21 touched entrypoints)
- docs/strata/waive.md (RELWAIVE002 emission cross-reference to the new helper)
- tests/unit/strata/test_waive.py (TestStaleRelwaiveViolations, 4 new tests)

<!-- frob:no-behavior-change reason="pure extraction of the byte-identical RELWAIVE002 stale-waiver emit block into _waive.py::stale_relwaive_violations, shared by all 21 call sites via a factory param; the rule id, message text, node, and sub_target emitted for every family are unchanged. Proved by: (1) full tests/unit/strata/ suite identical before/after -- 1379 passed / 3 pre-existing unrelated failures (test_export_golden.py::test_seccomp, ::test_k8s, test_mutation_audit.py::test_every_may_is_load_bearing -- reproduced on main before this diff too), (2) new direct unit tests on the helper itself." -->

Deliverable 1 (extraction): DONE. `stale_relwaive_violations(stale, make)` in
_waive.py builds one RELWAIVE002 violation per stale waiver via
`_stale_detail` (already existed) plus the caller's own violation type
(`make`); 20 call sites pass their class directly (constructor already
accepts rule/node/sub_target/detail), `_starvation.py` passes a small
lambda for its extra `resource=""` field. No violation TYPE was
collapsed -- each family still builds its own dataclass.

Deliverable 2 (DUP001 generalization verdict): DUP001 CAN already catch
this exact type-name-only-duplication shape -- no new detector logic is
needed. Empirically verified (see T-1957, will renumber at
land) against the pre-dedup `_backpressure.py`/`_fallback.py` pair:
default config (`region_kernel=False`) misses the
`check_backpressure_obligations`/`check_fallback_obligations` pair
entirely (3 unrelated cross-file hits only); turning on ONLY
`[dup].region_kernel=true` (R1.5, still no native rungs) finds it at
`rung=r1.5 similarity=1.0`, because R1.5 runs its suffix-array match over
the CORPUS'S R2-NORMALIZED (alpha-renamed) token stream at sub-symbol
region granularity (docs/modules/dup.md's own R1.5 section) -- exactly
"same shape, different identifier". It was invisible on this family only
because `[dup].region_kernel` ships off by default in this repo's
frob.toml (T-0193's perf-driven opt-in default), not because the
technique cannot see it. Filed T-1957 (residue, out of this
ticket's `src/frob/strata/` scope and flagged as a possible
`src/frob/dup/` collision zone this wave) to (a) add a permanent
regression test under tests/unit/dup/ reconstructing this exact
type-name-only shape, and (b) decide whether to flip `[dup].region_kernel`
on repo-wide (a separate perf-tradeoff call) or rely on (a) plus a docs
cross-reference.

Evidence: 4 new pytest node ids bound (tests/unit/strata/test_waive.py::
TestStaleRelwaiveViolations::{test_builds_one_violation_per_stale_waiver,
test_uses_stale_detail_message, test_empty_stale_yields_empty_tuple,
test_factory_lambda_can_add_extra_fields}); full tests/unit/strata/
suite run before AND after the extraction (see BEFORE/AFTER note above).

Filed: T-1957 "Wire DUP001 region_kernel (R1.5) as regression
corpus for type-name-only clone families (T-1938 finding)"
(scope: src/frob/dup/**, tests/unit/dup/**, docs/modules/dup.md)

Gates: `frob check --ticket T-1938` clean on every ticket-scoped gate
family (SCOPE 0 errors, PRE 0 errors, AFFECT 0 errors, WIRE 0 errors,
COV002/TODO001/FMT within the diff-driven scope 0 errors). Repo-wide
FAILs shown by the same run (ruff-format 78 files, gate:DOC/DRIFT in
src/frob/tickets/_land.py, gate:COV COV003/COV006/COV007 across
unrelated files) are pre-existing baseline debt, none in this ticket's
touched files -- confirmed unrelated by file path, not waived away.

### Changed
```
 tickets/T-1938/ticket.md           | 189 ++++++++++++++++++++++++++++++++++++-
 tickets/T-1957/ticket.md |  84 +++++++++++++++++
 2 files changed, 271 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/strata/test_waive.py::TestStaleRelwaiveViolations::test_builds_one_violation_per_stale_waiver` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_waive.py::TestStaleRelwaiveViolations::test_uses_stale_detail_message` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_waive.py::TestStaleRelwaiveViolations::test_empty_stale_yields_empty_tuple` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_waive.py::TestStaleRelwaiveViolations::test_factory_lambda_can_add_extra_fields` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 6 error(s), 876 warning(s), 700 waived
- error-findings: COV003@tickets/T-0185, COV003@tickets/T-1351, COV003@tickets/T-1507, COV003@tickets/T-1512, DOC002@src/frob/tickets/_land.py, DRIFT002@src/frob/tickets/_land.py
