---
id: T-0101
title: extend frob:waive to arch/perf tool channels or document the boundary
state: done
kind: feature
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/arch/**
- docs/**
- tickets.md
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestCoverageGate::test_waive002_flags_arch_category_as_ineffective
- tests/test_gates.py::TestCoverageGate::test_waive002_flags_unknown_rule_id_as_ineffective
- tests/test_gates.py::TestCoverageGate::test_waive002_end_to_end_via_run_gates
designated_repro_test: null
threat: null
component: null
---
typani campaign gap report: frob:waive suppresses gates-channel rule ids only; a waive on an arch long-function finding has no effect and fails silently. Either honor waivers in the arch/dup tool channels or make the waive command error when targeting an unwaivable channel.