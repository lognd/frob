---
id: T-0684
title: implement checkable-control enforcement for CWE weakness registry Top-25-class
  units
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/
- src/frob/strata/
- docs/design/registry/weaknesses.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_threat.py::TestEvalFiresCwe94::test_eval_capability_is_classified_not_benign_excused
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
---
Standing home for 27 weaknesses.yaml CWE entries (CWE-20,22,77,78,79,89,94,119,125,190,269,276,287,306,352,362,416,434,476,502,639,787,798,862,863,918,922 -- overlapping the CWE Top-25/OWASP classic set, relevant to T-0674's Top-25 tension follow-up) whose controls are machine-checkable but not yet enforced by any gate/check. They previously carried deferred:T-0384 (the reconciliation ticket itself) -- a self-reference that would orphan them the moment T-0384 closed; T-0384's pass re-pointed them here. Each entry needs either a real enforcing check (then flip to handled_by:<rule-id>) or a reasoned out_of_scope/not-checkable disposition.