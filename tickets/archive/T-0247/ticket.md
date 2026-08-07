---
id: T-0247
title: store grammar still missing on-deploy/observe/errors_total/panics_contained_by
  from node_prop
state: done
kind: bug
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- strata-core/src/parse.rs
- docs/strata/surface.md
- src/frob/strata/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_store_observability.py::TestStoreObservabilityGrammar::test_store_errors_total_and_panics_become_node_attrs
- tests/unit/strata/test_store_observability.py::TestStoreObservabilityGrammar::test_store_observe_generates_internal_flow_to_target
- tests/unit/strata/test_store_observability.py::TestStoreObservabilityGrammar::test_store_errors_total_without_observe_is_non_fatal
- tests/unit/strata/test_store_observability.py::TestStoreObservabilityFailClosed::test_store_panics_supervisor_must_be_declared
- tests/unit/strata/test_store_observability.py::TestStoreObservabilityFailClosed::test_store_observe_target_must_be_declared
- tests/unit/strata/test_store_observability.py::TestStoreObservabilityFailClosed::test_store_unknown_log_class_is_rejected
- tests/unit/strata/test_store_observability.py::TestStoreOnDeploy::test_store_on_deploy_lands_on_node_deploy_contract
- tests/unit/strata/test_store_observability.py::TestStoreOnDeploy::test_store_without_on_deploy_leaves_node_deploy_none
designated_repro_test: null
threat: null
component: null
---
found while working T-0166: docs/strata/surface.md's std.infra grammar block says store_prop := node_prop | engine | immutable | append_only | rpo, implying store accepts the FULL node_prop set. T-0166 closed the code/may gap (the one this ticket's scope named), but parse_store still has no branch for on deploy/observe/errors_total/panics_contained_by -- store_prop remains a real subset of node_prop, not the full union the grammar block literally claims. Either implement the remaining node_prop items on store (mirroring parse_node) or narrow the surface.md grammar line to enumerate the actual accepted subset instead of the misleading 'node_prop' alias.

Note: this ticket's `scope` field was originally authored as a single
comma-joined YAML list item (`strata-core/src/parse.rs,docs/strata/
surface.md,src/frob/strata/**,tests/**`) instead of four separate list
entries -- a pre-existing ticket-authoring bug that made `frob check`'s
SCOPE001 gate reject every intentionally-scoped file as out of scope.
Corrected to four list entries with the SAME globs (no scope widened or
narrowed), plus a fifth `tickets.md` entry added explicitly (the SAME
"add tickets.md to scope" convention every other ticket in this ledger
already uses for its own Done report, e.g. T-0166/T-0250) -- the
playbook's "tickets.md is always in scope, implicitly" note describes
practice, not a gate exemption; SCOPE001 checks the literal list.