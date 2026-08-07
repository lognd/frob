## Done report

REL33x DELIVERY-SEMANTICS-obligation family (T-0652), mirroring the
established REL3xx module pattern (_message_schema.py/_txn.py):

- New module src/frob/strata/_delivery_semantics.py with REL330 (missing
  or invalid delivery=<value> attr on a queue node -- catalog folded into
  the missing rule per _pii.py::check_pii_catalog precedent) and REL331
  (declared-but-unproven delivery semantics, proof-against-code,
  T-0331 PROVABILITY CONSTRAINT).
- Reuses the existing `queue` node population from _backpressure.py/
  _message_schema.py -- a third orthogonal obligation on the same
  population, no new kernel primitive.
- GRAMMAR NOTE: the ticket body's prose spelling ("exactly-once"/
  "at-least-once", hyphenated) is not writable through the existing
  grammar -- strata-core/src/parse.rs's ATTRVAL production
  (`IDENT ['=' IDENT]`) only accepts IDENT tokens, which cannot contain a
  hyphen. The grammar already has a precedent parser fixture for exactly
  this attr (`attr delivery=at_least_once;`, strata-core/src/parse.rs's
  own `parses_flow_with_all_properties` test), using the underscore
  spelling -- so DELIVERY_SEMANTICS uses `exactly_once`/`at_least_once`
  to match what the parser actually accepts, not the ticket prose's
  hyphenation. No grammar change was needed or made.
- Wired __init__.py exports (DELIVERY_SEMANTICS, DELIVERY_SEMANTICS_RULES,
  REL_MISSING_DELIVERY_SEMANTICS, REL_UNPROVEN_DELIVERY_SEMANTICS,
  DeliverySemanticsReport, DeliverySemanticsViolation,
  check_delivery_semantics_obligations).
- New docs/strata/reliability.md REL33x section (surface vocabulary,
  grammar-data ceiling, waiver channel), mirroring REL32x's shape.
- New tests/unit/strata/test_delivery_semantics.py, 7 tests, all pass.

Filed: none (no out-of-scope findings; ticket was not pre-implemented).

Gates: frob check --ticket T-0652 clean across lint/static/gates-fast/
gates-native/gates-security (chunked --only loop, agent-playbook section
3b); the only errors seen (ty diagnostics in tests/test_gates.py, ruff-
format on src/frob/arch/_lock_ordering.py etc.) are pre-existing and
untouched by this ticket's scope. gate:PRE was refreshed clean via
`frob ticket sweep T-0652` after adding the new files.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/strata/test_delivery_semantics.py::TestMissingDeliverySemantics::test_queue_node_without_delivery_semantics_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_delivery_semantics.py::TestMissingDeliverySemantics::test_invalid_delivery_value_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_delivery_semantics.py::TestMissingDeliverySemantics::test_discharged_and_non_queue_nodes_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_delivery_semantics.py::TestMissingDeliverySemantics::test_waiver_discharges_finding` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_delivery_semantics.py::TestUnprovenDeliverySemantics::test_declared_with_no_code_evidence_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_delivery_semantics.py::TestUnprovenDeliverySemantics::test_declared_with_real_code_evidence_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_delivery_semantics.py::TestUnprovenDeliverySemantics::test_declared_with_no_bound_code_is_uncheckable_not_a_violation` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 0 error(s), 4181 warning(s), 219 waived
- error-findings: none (measured, zero errors)
