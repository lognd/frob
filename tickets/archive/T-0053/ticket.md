---
id: T-0053
title: 'strata phase 4: code binding (tier 2) + self-hosting'
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0052
parent: T-0047
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- src/frob/lang/**
- src/frob/gates/**
- tests/**
- design/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_every_claim_proves
- tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_cross_component_import_without_declared_flow_is_a_violation
designated_repro_test: null
acceptance:
- text: GIVEN design/frob.strata WHEN frob check runs on this repo THEN SYS gates
    enforce frob's own declared architecture (self-hosting)
  evidence: []
threat: null
component: null
---
.strata as a 6th frob.lang grammar (design constructs become graph symbols with digests/acks/drift), code globs + import conformance, effect extraction vs may-capabilities, frob:channel/boundary/secret directives, SYS gate family in run_gates. Exit = frob gates on its own design.
## Done report

Phase-4 umbrella closed on completion of all five children, each
reviewed and merged separately: T-0077 (.strata as the sixth frob.lang
grammar), T-0078 (tier-2 code binding, exact-direction import
conformance), T-0079 (effect extraction vs may-capabilities), T-0080
(frob:channel/boundary/secret directives + SYS001-004 gates), T-0081
(self-hosting: design/frob.strata models frob with prover-verified
claims, CI-locked). Phase-4 exit criterion met per roadmap.md. Known
deferral: surface grammar cannot yet express code=/may attrs (T-0132).
Verification at close: frob check exit 0 with the bundled tool, full
suite green.