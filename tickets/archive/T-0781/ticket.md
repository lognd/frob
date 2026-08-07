---
id: T-0781
title: 'vet/gates: taint rule -- repo-writable state (.git/.frob JSON or text) reaching
  subprocess argv requires validation or ''--'''
state: done
kind: security
origin: auditor
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- src/frob/gates/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/vet/test_taint.py::TestTaintFindings::test_unvalidated_state_read_reaching_argv_fires
- tests/unit/vet/test_taint.py::TestTaintFindings::test_validated_value_does_not_fire
- tests/unit/vet/test_taint.py::TestTaintFindings::test_dash_dash_terminator_clears_taint
- tests/unit/vet/test_taint.py::TestTaintFindings::test_non_state_read_does_not_fire
- tests/unit/vet/test_taint.py::TestTaintFindings::test_dynamic_argv_list_is_not_falsely_cleared
- tests/unit/vet/test_taint.py::TestTaintFindings::test_unparseable_file_returns_empty
- tests/unit/vet/test_taint.py::TestTaintGate::test_taint_gate_no_findings_on_empty_tracked_set
- tests/unit/vet/test_taint.py::TestTaintGate::test_taint_gate_emits_warn_severity_violation
designated_repro_test: null
acceptance:
- text: GIVEN a fixture where a value parsed from a file under .git/ or .frob/ flows
    into a subprocess argv position without passing a registered validator or a preceding
    -- literal WHEN the check runs THEN a finding fires naming source and sink; GIVEN
    the same flow through a validator THEN no finding
  evidence:
  - tests/unit/vet/test_taint.py::TestTaintGate::test_taint_gate_emits_warn_severity_violation
threat: null
component: null
---
Audit M1 gate-direction: SEC gates catch shell=True and f-string-into-argv but not the trust-boundary shape (peer-writable state file -> argv). Model the source set (read_text/json.loads on .git//.frob paths) and the sink (subprocess/run_argv argv positions); require a validator hop or -- terminator. Same rule covers worktree paths reaching Path.exists/display. This is a dataflow rule -- scope it honestly as intra-module flow first, interprocedural later.