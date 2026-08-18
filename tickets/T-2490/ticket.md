---
id: T-2490
title: 'SYS100: T-2411''s wiring test in test_lang_conformance_gate.py declares no
  exec capability'
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description

T-2411 (wire LANG004 capability_conformance_gate into the check job
table, landed 918ec0c7d0675c95e5afa3a468fe3738c13dbc56) added a new
positive-control wiring test,
tests/test_lang_conformance_gate.py::TestCapabilityConformanceWiring::test_capability_conformance_fires_through_real_gate_dispatch,
which calls subprocess.run(["git", ...]) five times (lines 384, 385,
390, 407, 408) to build a throwaway git repo fixture for an end-to-end
run_gates() dispatch check. This is a genuine new `exec` capability
site on the `testsuite` node that design/frob.strata does not declare
-- SELFAUDIT001/SYS100 now fires 5 times for it.

Found while working T-2488 (an unrelated capability-via-ratchet.lock.json
ceiling bump) -- discovered via a `frob check --only sys` run, out of
T-2488's own declared scope (docs/design/registry/capability-via-ratchet.lock.json
only). Filed rather than fixed inline, per scope discipline.

## Plan

Add tests/test_lang_conformance_gate.py to the testsuite node's `may
"exec" via ...` declaration in design/frob.strata (it already contains
many other tests/*.py files using subprocess.run for git fixture setup
-- same shape, same reason). Verify SYS100 clears for this file
afterward with `frob check --only sys`.