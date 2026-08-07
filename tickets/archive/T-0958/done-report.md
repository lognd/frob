## Done report

Changed:
docs/design/registry/system-design.yaml (56 rows re-dispositioned; header note updated)
src/frob/strata/_distributed_txn.py::check_distributed_txn_obligations (frob:enforces SDC-4-DISTRIBUTED-TRANSACTIONS, SDC-4-OUTBOX-SAGA-PATTERNS)
src/frob/strata/_delivery_semantics.py::check_delivery_semantics_obligations (frob:enforces SDC-4-EXACTLY-ONCE-PROCESSING, SDC-5-IDEMPOTENT-RECEIVER, SDC-8-AT-MOST-ONCE, SDC-8-AT-LEAST-ONCE, SDC-8-IDEMPOTENT-CONSUMERS)
src/frob/strata/_retry.py::check_retry_obligations (frob:enforces SDC-4-IDEMPOTENCY, SDC-5-RETRY-BACKOFF-JITTER)
src/frob/strata/_reliability.py::check_reliability_timeouts (frob:enforces SDC-5-TIMEOUT)
src/frob/strata/_backpressure.py::check_backpressure_obligations (frob:enforces SDC-5-LOAD-SHEDDING)
src/frob/strata/_observability.py::check_observability_obligations (frob:enforces SDC-6-USE-METHOD-UTILIZATION-SATURATION-ERRORS, SDC-7-THREE-PILLARS-METRICS-LOGS-TRACES, SDC-7-DISTRIBUTED-TRACING-DAPPER)
src/frob/strata/_slo.py::check_slo_obligations (frob:enforces SDC-7-SLO-BASED-ALERTING)
src/frob/strata/_clock_ordering.py::check_clock_ordering_obligations (frob:enforces SDC-8-ORDERING-GUARANTEES)
src/frob/strata/_message_schema.py::check_message_schema_obligations (frob:enforces SDC-13-EVERY-SERVICE-TO-SERVICE-API-DECLARES-AN-EXPLICIT-SCHEMA-CONTRACT-WITH-A-VERSIONING)
src/frob/gates/__init__.py::_KNOWN_GATE_RULES (added REL200/220/221/260/270/272/280/320/330/350/370, the exact ids this ticket's handled_by dispositions cite -- REG002 needs them in known_rules to resolve)

Disposition counts (56 rows, all previously deferred:T-0958):
  handled_by: 17 (REL200 x1, REL220 x1, REL221 x1, REL260 x1, REL270 x2, REL272 x1, REL280 x1, REL320 x1, REL330 x5, REL350 x2)
  deferred: 4 (to 2 new child tickets, 2 rows each -- see Filed)
  out_of_scope: 35 (7 network-fallacy descriptive concepts, 10 named consensus/replication algorithms frob does not implement, 6 replication/sharding architecture patterns, 2 db-transaction/CDC descriptive concepts, 1 meta-concept, 1 tail-latency descriptive phenomenon, 1 named-practice/person citation, 1 log-abstraction descriptive concept, 6 deployment/ops methodology patterns)

Enforces edges added: 17 `frob:enforces <SDC-id>` directives across the 9 strata modules listed above (one per handled_by row), each paired with the disposition's target rule.

Filed:
T-0962 -- static checks: ABI/ISA compat-window stability + boot-chain signed/measured attestation obligations (feature; 2 sec-13 rows deferred here)
T-0960 -- static checks: kernel/userspace-interface classification + per-process cgroup resource-bound declaration obligations (feature; 2 sec-13 rows deferred here)
T-0961 -- gates/__init__.py _KNOWN_GATE_RULES missing the bulk of the REL26x-REL38x + SYS204 obligation-family rule ids (bug; the broader listing-omission this ticket only partially closed, scoped to just the 11 ids it needed)

Evidence:
tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_declared_total_is_119 -- pass
tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_audit_reports_exhausted -- pass
tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_every_deferred_entry_targets_an_open_ticket -- pass
tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_no_entry_defers_to_this_reconciliation_ticket -- pass
tests/test_registry_reconciliation_system_design.py::TestExhaustivenessGateOverRealSystemDesign::test_no_system_design_violations -- pass
Also observed passing (not separately bound as evidence): full tests/test_registry_reconciliation_system_design.py (8/8), tests/test_registry_exhaustiveness.py (33/33), tests/unit/strata/test_{retry,reliability,backpressure,observability,slo,clock_ordering,message_schema,distributed_txn,delivery_semantics}.py (all pass), tests/test_gates.py -k KnownGateRuleIds (pass).

Gates: `frob check --ticket T-0958` chunked (prework, scope, coverage, doclink, docanchor, registry) all pass 0 errors after re-running `frob ticket sweep T-0958` post scope-add. `frob check --ticket T-0958 --only registry` shows 0 violations of any severity attributed to docs/design/registry/system-design.yaml (REG002/REG008/REG011 clean).

### Changed
(no changed files detected)

### Evidence
- `tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_declared_total_is_119` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_audit_reports_exhausted` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_every_deferred_entry_targets_an_open_ticket` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_no_entry_defers_to_this_reconciliation_ticket` (pytest node id, verified passing when recorded)
- `tests/test_registry_reconciliation_system_design.py::TestExhaustivenessGateOverRealSystemDesign::test_no_system_design_violations` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 4971 warning(s), 220 waived
- error-findings: none (measured, zero errors)
