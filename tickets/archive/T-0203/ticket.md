---
id: T-0203
title: 'perf_gate: silence UnsupportedLanguage skips for non-code files'
state: done
kind: bug
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/perf/**
- src/frob/gates/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestOptInGates::test_perf_gate_flags_list_membership_in_loop
- tests/test_gates.py::TestOptInGates::test_perf_gate_silences_unscannable_files
- tests/test_gates.py::TestOptInGates::test_perf_gate_still_reports_genuine_parse_failure
- tests/test_gates.py::test_gates_run_gates_integration
designated_repro_test: null
threat: null
component: null
---
User report 2026-07-18: 'perf_gate: skipping unparsed docs/guides/agent-playbook.md: UnsupportedLanguage: File extension has no registered grammar' -- perf gate walks non-code files (markdown/json/toml) and logs a WARN-looking skip for each. Files with no registered grammar are not perf-scannable BY DESIGN: filter them out before the scan by extension (reuse the canonical language registry extension table from T-0129), log nothing at default verbosity (a single DEBUG-level count line at most). A skip message should be reserved for files that SHOULD parse but failed. Test: perf gate over a fixture tree with md/toml/json emits zero skip lines and scans only registered-grammar files.