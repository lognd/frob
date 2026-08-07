## Done report

Implements REL25x (T-0645): REL250 SPOF detection -- a node receiving at least
one `critical` inbound flow whose declared capacity is a structural singleton
(node.capacity is None, defaulting to Capacity's own replicas_max=1, or a
declared Capacity with replicas_max==1 per Capacity.singleton) and does not
carry the `redundant` exemption attr. Deny-by-default with a reasoned waive
channel (T-0174), same discipline as the rest of this REL2xx ticket cluster.

Unlike T-0640/T-0641/T-0642/T-0643, REL25x is ONE rule, not a missing/unproven
pair: SPOF is a structural fact readable straight off KernelModel.nodes/
.flows (Capacity.replicas_max is already a typed int field, not a bare attr
needing proof-against-code), so this module does not use
_obligation_proof.py and check_spof returns a bare SpofReport, not a
Result[...] (no bind_code call, cannot Err).

`critical` (Flow attr, this module) deliberately reuses T-0642's exact string
(CRITICAL_ATTR, a Node attr there) at a different grammar site rather than
importing it -- documented in the module docstring as intentional, not a
naming collision.

New: src/frob/strata/_spof.py, tests/unit/strata/test_spof.py (6 tests:
firing on default/declared singleton capacity, clean on replicated capacity,
clean on redundant exemption, clean on non-critical flow, waiver keeps
sibling finding). docs/strata/reliability.md gets a new "REL25x: SPOF
detection (T-0645)" section.

Verification: `uv run pytest tests/unit/strata/test_spof.py -p no:cacheprovider
-q` -> 6 passed. `frob check --only lint/static/gates-fast/gates-native/
gates-security --ticket T-0645` all clean (0 errors across every stage).

Cuts: none against the ticket's declared plan. `critical`/`redundant` are
bare presence-only markers (same grammar-data ceiling as the rest of this
cluster); no strata-core change (out of scope).

### Changed
```
 docs/strata/reliability.md                 | 232 ++++++++++++++++++-
 src/frob/strata/__init__.py                |  50 ++++
 src/frob/strata/_circuit_breaker.py        | 318 ++++++++++++++++++++++++++
 src/frob/strata/_fallback.py               | 262 +++++++++++++++++++++
 src/frob/strata/_obligation_proof.py       | 111 +++++++++
 src/frob/strata/_retry.py                  | 351 +++++++++++++++++++++++++++++
 src/frob/strata/_waive.py                  |   6 +
 tests/unit/strata/test_circuit_breaker.py  | 170 ++++++++++++++
 tests/unit/strata/test_fallback.py         | 138 ++++++++++++
 tests/unit/strata/test_obligation_proof.py |  77 +++++++
 tests/unit/strata/test_retry.py            | 244 ++++++++++++++++++++
 tickets.md                                 | 179 ++++++++++++++-
 12 files changed, 2131 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/unit/strata/test_spof.py::TestSpof::test_singleton_node_with_critical_inbound_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_spof.py::TestSpof::test_declared_singleton_capacity_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_spof.py::TestSpof::test_replicated_capacity_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_spof.py::TestSpof::test_redundant_exemption_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_spof.py::TestSpof::test_non_critical_flow_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_spof.py::TestSpof::test_waiver_on_one_node_keeps_sibling_node_finding` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
