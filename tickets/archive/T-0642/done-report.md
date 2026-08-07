## Done report

Implements REL23x (T-0642): REL230 missing circuit-breaker/bulkhead on an
`external` node, REL231 declared-but-unproven circuit breaker (proof-against-
code, T-0331 PROVABILITY CONSTRAINT). Extends LINT004's kill-switch idea (a
risky capability needs an operator escape hatch) to a new population: a node
that depends on something external needs its own escape hatch against that
dependency's failure. Mirrors T-0640/T-0641's structure and reuses
_obligation_proof.py's shared proof-against-code plumbing (T-0641).

Also defines CRITICAL_ATTR ("critical" bare marker) and is_critical_dependency
in this module rather than in _fallback.py, because T-0643 (blocked_by this
ticket) reuses this exact dependency-criticality classification per its own
ticket body -- one shared home for the marker rather than two copies.

New: src/frob/strata/_circuit_breaker.py, tests/unit/strata/test_circuit_breaker.py
(8 tests: predicates + REL230 firing/clean/waived + REL231
firing/discharged/uncheckable). docs/strata/reliability.md gets a new
"REL23x: CIRCUIT BREAKER / bulkhead obligation (T-0642)" section.

REL230/REL231 are node-scoped, single-instance-per-node (a node has at most
one `external` marker), so they are NOT added to
_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES -- same carve-out as REL210/REL211.

Verification: `uv run pytest tests/unit/strata/test_circuit_breaker.py
tests/unit/strata/test_retry.py tests/unit/strata/test_reliability.py
tests/unit/strata/test_obligation_proof.py -p no:cacheprovider -q` -> 52
passed. `frob check --only lint/static/gates-fast/gates-native/gates-security
--ticket T-0642` all clean (0 errors across every stage).

Cuts: none against the ticket's declared plan. `external`/`circuit_breaker`/
`critical` are bare presence-only markers (same grammar-data ceiling as
T-0640/T-0641), no strata-core change (out of this ticket's scope).

### Changed
```
 docs/strata/reliability.md                 |  93 +++++++-
 src/frob/strata/__init__.py                |  16 ++
 src/frob/strata/_obligation_proof.py       | 111 +++++++++
 src/frob/strata/_retry.py                  | 351 +++++++++++++++++++++++++++++
 src/frob/strata/_waive.py                  |   6 +
 tests/unit/strata/test_obligation_proof.py |  77 +++++++
 tests/unit/strata/test_retry.py            | 244 ++++++++++++++++++++
 tickets.md                                 |  95 +++++++-
 8 files changed, 989 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/strata/test_circuit_breaker.py::TestPredicates::test_is_external_dependency` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_circuit_breaker.py::TestPredicates::test_is_critical_dependency` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_circuit_breaker.py::TestMissingCircuitBreaker::test_external_node_without_circuit_breaker_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_circuit_breaker.py::TestMissingCircuitBreaker::test_discharged_and_non_external_nodes_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_circuit_breaker.py::TestMissingCircuitBreaker::test_waiver_on_one_node_keeps_sibling_node_finding` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_circuit_breaker.py::TestUnprovenCircuitBreaker::test_declared_with_no_code_evidence_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_circuit_breaker.py::TestUnprovenCircuitBreaker::test_declared_with_real_code_evidence_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_circuit_breaker.py::TestUnprovenCircuitBreaker::test_declared_with_no_bound_code_is_uncheckable_not_a_violation` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
