---
id: T-0115
title: 'threat F: frob sys audit exhaustiveness matrix + DOC002 + vuln litmus'
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0114
parent: T-0109
tier: ticket
sprint: null
scope:
- docs/strata/**
- docs/commands/sys.md
- src/frob/strata/**
- src/frob/app/sys_runner.py
- src/frob/app/config.py
- src/frob/__main__.py
- design/litmus/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_audit.py::TestExhaustiveness::test_clean_proved
- tests/unit/strata/test_audit.py::TestExhaustiveness::test_unknown_view_errs
- tests/unit/strata/test_audit.py::TestVulnLitmus::test_refutes_gap_per_family
- tests/unit/strata/test_audit.py::TestHardenedLitmus::test_hardened_clean
- tests/unit/strata/test_litmus_audit_vuln.py::TestAuditVulnGolden::test_may_sql_parses_and_elaborates
- tests/unit/strata/test_litmus_audit_vuln.py::TestAuditVulnGolden::test_fires_undischarged_in_security_and_quality
- tests/system/test_cli_sys_audit.py::TestSysAuditCli::test_clean_model_exits_zero
- tests/system/test_cli_sys_audit.py::TestSysAuditCli::test_undischarged_capability_exits_nonzero_with_named_gap
- tests/system/test_cli_sys_audit.py::TestSysAuditCli::test_no_design_dir_is_a_noop
designated_repro_test: null
acceptance:
- text: GIVEN a deliberately vulnerable+unoptimized litmus WHEN frob sys audit runs
    THEN every planted anti-pattern is flagged per family; hardened twin discharges
    all; overclaiming README fails DOC002
  evidence: []
threat: null
component: null
---
frob sys audit per-family exhaustiveness matrix; DOC002 binds security/quality prose to a PROVED audit; design/litmus/vulnerable.strata + hardened twin as goldens. threat.md phase F.