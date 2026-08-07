---
id: T-0054
title: 'strata phase 5: std.secrets, std.deploy, work-order compiler, exporters'
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0053
parent: T-0047
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- tests/**
- design/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_k8s
- tests/unit/strata/test_secrets.py::TestReadersExactSetClosure::test_readers_claim_proved_on_exact_match
designated_repro_test: null
acceptance:
- text: GIVEN a refuted or undischarged claim WHEN frob sys plan runs THEN scoped
    tickets are filed idempotently and a sys ticket cannot close until its claim discharges
    at the required rung
  evidence: []
threat: null
component: null
---
Credentials as cache-of-authority (lifetime/revocation obligations), deployment as endorsement pipeline (canary schedules, rollback budgets, vet as endorsement evidence), frob sys plan obligation->ticket compiler, frob sys doc generator + DOC002 claims audit, k8s-netpol/seccomp/IAM exporters.
## Done report

Phase-5 umbrella closed on completion of all five children, each
reviewed and merged separately: T-0082 std.secrets (credentials as
cache-of-authority), T-0083 std.deploy (endorsement/canary/rollback),
T-0084 frob sys plan (the obligation -> ticket work-order compiler),
T-0085 frob sys doc + DOC003 claims audit, T-0086 config exporters
(k8s netpol / seccomp / IAM). Surface grammar for the phase's
constructs landed alongside via T-0132/T-0136/T-0138. Verified at
close: full suite green, frob check exit 0.