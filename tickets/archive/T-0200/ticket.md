---
id: T-0200
title: add real kill-switch/feature-flag mechanism for exec/net capabilities (checker/core/stratamod/vet)
state: done
kind: feature
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/process/**
- src/frob/check/**
- src/frob/strata/**
- design/frob.strata
- tickets.md
- tests/test_process.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_process.py
  reason: T-0200 process work maps to tests/test_process.py
  actor: logan
  at: '2026-07-20'
evidence:
- tests/unit/test_process_guard.py::TestExecEnabled::test_truthy_values_disable
- tests/unit/test_process_guard.py::TestGuardedSubprocessRun::test_disabled_returns_err_without_spawning
designated_repro_test: null
threat: null
component: null
---
T-0155's LINT004 rule (design lint family) fires honestly on design/frob.strata's checker/core/stratamod/vet nodes: each holds a risky (exec/net) may capability with no real, checked-in kill switch (env var / feature flag) an operator can flip live to disable it. T-0155 deliberately did not fabricate a flag=<id> attr naming a mechanism that does not exist (declare real facts or waive with reasons, T-0150/T-0151 precedent) -- this ticket is the follow-on product work to build the actual mechanism and then discharge LINT004 for real on design/frob.strata.