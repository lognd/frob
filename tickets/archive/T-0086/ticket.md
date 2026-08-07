---
id: T-0086
title: 'strata exporters: k8s netpol / seccomp / IAM from the model'
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0053
parent: T-0054
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- src/frob/app/**
- src/frob/__main__.py
- tests/**
- docs/commands/**
- docs/index.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_export.py::TestExportK8sNetpol::test_deny_by_default
- tests/unit/strata/test_export.py::TestExportK8sNetpol::test_ingress_from_src
- tests/unit/strata/test_export.py::TestExportK8sNetpol::test_egress_to_dst
- tests/unit/strata/test_export.py::TestExportK8sNetpol::test_foreign_peer
- tests/unit/strata/test_export.py::TestExportK8sNetpol::test_stable
- tests/unit/strata/test_export.py::TestExportSeccomp::test_no_may_baseline
- tests/unit/strata/test_export.py::TestExportSeccomp::test_exec_allows_exec
- tests/unit/strata/test_export.py::TestExportSeccomp::test_net_allows_socket
- tests/unit/strata/test_export.py::TestExportSeccomp::test_default_errno
- tests/unit/strata/test_export.py::TestExportSeccomp::test_stable
- tests/unit/strata/test_export.py::TestExportIam::test_flow_statements
- tests/unit/strata/test_export.py::TestExportIam::test_no_flows_empty
- tests/unit/strata/test_export.py::TestExportIam::test_stable
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_k8s
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_iam
- tests/system/test_cli_sys_export.py::TestCliSysExport::test_k8s_export_is_valid_yaml
- tests/system/test_cli_sys_export.py::TestCliSysExport::test_seccomp_export_is_valid_json
- tests/system/test_cli_sys_export.py::TestCliSysExport::test_iam_export_is_valid_json
- tests/system/test_cli_sys_export.py::TestCliSysExport::test_deterministic_across_two_processes
- tests/system/test_cli_sys_export.py::TestCliSysExport::test_missing_design_file_errors
- tests/system/test_cli_sys_export.py::TestCliSysExport::test_bad_format_errors
designated_repro_test: null
threat: null
component: null
---
The model compiles to runtime enforcement so static proofs are backed by defense-in-depth that cannot diverge; exported artifacts digest-stamped as evidence.

Scope widened beyond the original strata/**+tests/** at implementation time:
the assigning instructions required a minimal `frob sys export` CLI (T-0084's
`sys` group had not landed on main), which necessarily touches
src/frob/app/{config.py,app.py,sys_runner.py} and src/frob/__main__.py, plus
a new docs/commands/sys.md linked from docs/index.md.