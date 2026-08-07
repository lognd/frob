---
id: T-0946
title: investigate shared walk for sys/secrets/pii_structural gates
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: T-0927
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- docs/audits/check-performance.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/audits/check-performance.md
  reason: ticket explicitly requires recording before/after in the audit remediation
    log
  actor: logan
  at: '2026-07-27'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- tests/test_secrets_gate.py::TestGateIsGreenOnItself::test_repo_is_clean
designated_repro_test: null
threat: null
component: null
---
Found while working T-0928 (frob-check-performance audit). Three
process-pool gates -- sys (SEC1xx capability scan), secrets, and
pii_structural -- each independently walk (a variant of) the tracked
source-file set and parse/scan file content, measured at 6.22s/2.87s/4.60s
respectively in a representative `--only gates-security` run. This is a
cross-GATE duplicate-walk shape PERF007 (T-0413) does not catch (PERF007
matches a single NAMED call repeated across call sites, not three distinct
gates each independently walking what happens to be the same file set).
Investigate whether these three gates can share one walk + one parsed-tree
pass; do not blind-fix without confirming the file sets and scan needs
actually overlap. See docs/audits/check-performance.md Finding 4.