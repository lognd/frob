---
id: T-0228
title: check summary conflates errors and warnings ('pass ... 987 violation(s)')
state: done
kind: ux
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/check_runner.py
- src/frob/check/_python.py
- src/frob/gates/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_check.py::TestSummarySeverityHonesty::test_warn_only_gate_summary_splits_errors_and_warnings
- tests/unit/test_check.py::TestSummarySeverityHonesty::test_cycle_summary_splits_by_severity
designated_repro_test: null
threat: null
component: null
---
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 13 (all 3 repos; honesty risk): 'pass gates 987 violation(s), 0 waived' on exit 0, 'pass frob-cycle 1 cycle found', and failing lines counting warn-class findings as violations. Split every summary line into N error(s), M warning(s), K waived; never label warn findings violations on a passing gate. Builds on T-0202's output work.