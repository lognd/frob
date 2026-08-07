## Done report

Found the REL27x observability+correlation obligation family
(`src/frob/strata/_observability.py`) already fully implemented and merged
to `main` on worktree warm-up (`git merge main` + `make core`), by a prior
session (this ticket was previously leased in a dead session, per dispatch
note). No code changes were needed against this ticket's scope
(`src/frob/strata/**`, `docs/strata/**`, `tests/unit/strata/**`) -- verified
the existing implementation against both acceptance criteria and the full
gate set instead of re-implementing.

REL270 (missing observability -- a `Boundary`-attached flow with no
`observability` attr), REL271 (declared-but-unproven observability,
proof-against-code via `_obligation_proof.py`'s shared owner-index/
bound-code/token-scan plumbing), and REL272 (missing correlation
propagation -- a non-first-hop chained flow with no `correlation` attr) all
mirror the REL2xx module structure `_backpressure.py`/`_ssot.py` establish
(same `Report`/`Violation` pydantic pair, flow-scoped multi-instance
findings registered in `_waive.py`, public surface wired into
`src/frob/strata/__init__.py`). Docs already present at
`docs/strata/reliability.md#rel27x-observability--correlation-obligation-t-0647`.

Tests: `tests/unit/strata/test_observability.py`, 8 cases covering REL270
(boundary flow fires, discharged/non-boundary clean, waiver keeps sibling
finding), REL271 (unproven fires, proven discharges, no-bound-code
uncheckable), REL272 (second-hop chained flow fires, first-hop/discharged
clean); plus `tests/unit/strata/test_registry_cross_refs.py`'s 4 cases
covering this and sibling REL2xx families' registry cross-refs.

Measured:
- `uv run pytest -q tests/unit/strata/test_observability.py
  tests/unit/strata/test_registry_cross_refs.py` -> 12 passed.
- `uv run frob check --ticket T-0647 --only gates-fast` -> PASS 0 errors.
- `uv run frob check --ticket T-0647 --only gates-native` -> PASS 0 errors.
- `uv run frob check --ticket T-0647 --only lint` -> PASS 0 errors.
- `uv run frob check --ticket T-0647 --only static` -> PASS (frob-exports/
  frob-dup/frob-arch/frob-cycle all pass; only pre-existing repo-wide
  suggestions).
- `uv run frob check --ticket T-0647 --only gates-security` -> gate:SELFAUDIT
  FAILs with 5 errors, but all 5 are the pre-existing, already-filed T-0910
  finding (`src/frob/arch/_logging_checks.py` exec/net/fetch_url capabilities
  undeclared on the `graphlang` design node) -- confirmed via `tickets.md`
  grep, unrelated to REL27x/T-0647 and out of this ticket's scope
  (design/frob.strata beyond the obligation itself is explicitly off-limits
  per dispatch). No other gate:SELFAUDIT or other-family findings touch
  `_observability.py`.

Cuts: none against the stated acceptance criteria.

### Changed
(no changed files -- implementation was already complete on main)

### Evidence
- `tests/unit/strata/test_observability.py::TestMissingObservability::test_boundary_flow_without_observability_fires` (pytest node id, verified passing)
- `tests/unit/strata/test_observability.py::TestMissingObservability::test_discharged_and_non_boundary_flows_clean` (pytest node id, verified passing)
- `tests/unit/strata/test_observability.py::TestMissingObservability::test_waiver_on_one_flow_keeps_sibling_flow_finding` (pytest node id, verified passing)
- `tests/unit/strata/test_observability.py::TestUnprovenObservability::test_declared_with_no_code_evidence_fires` (pytest node id, verified passing)
- `tests/unit/strata/test_observability.py::TestUnprovenObservability::test_declared_with_real_code_evidence_discharges` (pytest node id, verified passing)
- `tests/unit/strata/test_observability.py::TestUnprovenObservability::test_declared_with_no_bound_code_is_uncheckable_not_a_violation` (pytest node id, verified passing)
- `tests/unit/strata/test_observability.py::TestMissingCorrelation::test_second_hop_without_correlation_fires` (pytest node id, verified passing)
- `tests/unit/strata/test_observability.py::TestMissingCorrelation::test_first_hop_and_discharged_hop_clean` (pytest node id, verified passing)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: gates-fast/gates-native/lint/static all PASS; gates-security
  gate:SELFAUDIT fails on pre-existing out-of-scope T-0910 finding only
- error-findings: none against T-0647's own scope
