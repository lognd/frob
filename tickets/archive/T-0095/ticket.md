---
id: T-0095
title: 'frob check --delta: report only violations new since a stamped baseline'
state: done
kind: ux
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/check/**
- src/frob/gates/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestBaselineDelta::test_delta_filters_known_violations
- tests/test_gates.py::TestBaselineDelta::test_baseline_stale_when_file_changes
- tests/unit/test_check.py::TestRunGatesDelta::test_no_baseline_falls_back_to_full_set_with_warning
designated_repro_test: null
threat: null
component: null
---
Agentic token sink measured during the strata build: every frob check run prints ~90 pre-existing warn-level violations (ticketed legacy debt), and each implementer agent runs check 3-6 times per ticket, paying to re-read the same noise. Add a baseline stamp (like coverage-stamp) plus --delta mode that prints only violations absent from the baseline; frob check --stamp-baseline records it. Warn-dial stays for humans; agents get signal only.