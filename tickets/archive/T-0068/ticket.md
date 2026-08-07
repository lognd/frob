---
id: T-0068
title: strata std.policy.analyzable base pack + enables soundness cascade
state: done
kind: security
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0050
parent: T-0051
tier: ticket
sprint: null
scope:
- docs/strata/**
- tickets.md
- strata-core/**
- Makefile
- .github/**
- design/litmus/**
- src/frob/strata/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_packs.py::TestAutoInjection::test_trusted_component_without_pack_gets_it_injected
- tests/unit/strata/test_packs.py::TestEnablesCascade::test_waived_pack_downgrades_noflow_but_not_bound
- tests/unit/strata/test_packs.py::TestEnablesCascade::test_end_to_end_parse_elaborate_compile_evaluate
- tests/unit/strata/test_packs.py::TestEnablesCascade::test_waiving_a_policy_that_enables_nothing_downgrades_nothing
- tests/unit/strata/test_packs.py::TestEnablesCascade::test_waiving_a_nonexistent_policy_id_is_a_logged_no_op
designated_repro_test: null
threat: elevation-of-privilege
component: null
---
Mandatory for trusted components: no eval/exec/dynamic import/reflection dispatch, FFI only via frob bind, anti-aliasing rules. Policies declare enables; waiving one downgrades every dependent claim PROVED -> ASSUMED automatically.