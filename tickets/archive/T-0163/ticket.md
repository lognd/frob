---
id: T-0163
title: frob sys audit <file> appends bogus path segment instead of erroring
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/sys_runner.py
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_cli_sys_audit.py::TestSysAuditCli::test_file_arg_fails
- tests/system/test_cli_sys_audit.py::TestSysAuditCli::test_clean_model_exits_zero
- tests/system/test_cli_sys_audit.py::TestSysAuditCli::test_undischarged_capability_exits_nonzero_with_named_gap
- tests/system/test_cli_sys_audit.py::TestSysAuditCli::test_no_design_dir_is_a_noop
designated_repro_test: null
threat: null
component: null
---
Typani pilot: frob sys audit <file.strata> misbehaves silently, appending a bogus path segment; only frob sys audit . works. A file argument must either work (resolve to its containing design root) or fail loudly with a clear message naming the expected invocation. Vacuous-pass doctrine: silent path mangling is the worst outcome. Repro against typani's design/typani.strata layout.