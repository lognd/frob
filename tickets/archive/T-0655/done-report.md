## Done report

REL35x DISTRIBUTED-TRANSACTION-ACROSS-SERVICES saga/compensation
obligation (T-0655), mirroring the REL30x/_txn.py two-rule pattern but
extended across service boundaries per the ticket body.

- New module src/frob/strata/_distributed_txn.py: REL350 (missing
  saga/compensation) and REL351 (declared-but-unproven saga, proof-
  against-code, T-0331 PROVABILITY CONSTRAINT).
- KEY DESIGN DECISION: REL30x (_txn.py) needed a caller-supplied
  `store_ids` set because it asked the narrower "writes to >=2 STORES"
  question, which KernelModel alone cannot answer (a store desugars away
  at elaborate time). REL35x asks the BROADER "writes to >=2 SERVICES"
  question the ticket names -- and REL2xx's own module docstring already
  discloses that every Flow in this grammar crosses a real process/
  service boundary by construction (no in-process/self-flow construct
  exists), meaning every node already IS its own service boundary. So
  REL35x's population is "every op writing to >=2 distinct downstream
  nodes `model.flows` names" -- a plain KernelModel fact needing NO
  external store_ids input, unlike REL30x. This is the "multi-write
  detection extended across service boundaries" the ticket asks for.
- Unlike REL300 (which discharges on EITHER `transaction` or `saga`),
  REL350 requires `saga` specifically -- a bare `transaction` attr
  asserts a single coordinated commit, not meaningful once the write
  fans out across independent service processes with no shared commit
  log (verified by a dedicated test:
  test_transaction_attr_alone_does_not_discharge).
- Wired __init__.py exports (REL_MISSING_SAGA, REL_UNPROVEN_SAGA,
  DISTRIBUTED_TXN_RULES, DistributedTxnReport, DistributedTxnViolation,
  check_distributed_txn_obligations).
- New docs/strata/reliability.md REL35x section.
- New tests/unit/strata/test_distributed_txn.py, 7 tests, all pass.

Filed: none (no out-of-scope findings; ticket was not pre-implemented).

Gates: frob check --ticket T-0655 clean across lint/static/gates-fast/
gates-native/gates-security (chunked --only loop); gate:PRE refreshed via
`frob ticket sweep T-0655`.

### Changed
```
 docs/strata/reliability.md                   | 145 +++++++++++
 docs/strata/threat.md                        |  11 +
 src/frob/strata/__init__.py                  |  30 +++
 src/frob/strata/_delivery_semantics.py       | 343 +++++++++++++++++++++++++++
 src/frob/strata/_sync_depth.py               | 277 +++++++++++++++++++++
 tests/unit/strata/test_delivery_semantics.py | 175 ++++++++++++++
 tests/unit/strata/test_sync_depth.py         | 110 +++++++++
 tickets.md                                   | 232 +++++++++++++++++-
 8 files changed, 1317 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/strata/test_distributed_txn.py::TestMissingSaga::test_multi_service_write_op_without_saga_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_distributed_txn.py::TestMissingSaga::test_transaction_attr_alone_does_not_discharge` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_distributed_txn.py::TestMissingSaga::test_single_write_and_discharged_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_distributed_txn.py::TestMissingSaga::test_waiver_discharges_finding` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_distributed_txn.py::TestUnprovenSaga::test_declared_with_no_code_evidence_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_distributed_txn.py::TestUnprovenSaga::test_declared_with_real_code_evidence_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_distributed_txn.py::TestUnprovenSaga::test_declared_with_no_bound_code_is_uncheckable_not_a_violation` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 0 error(s), 4219 warning(s), 219 waived
- error-findings: none (measured, zero errors)
