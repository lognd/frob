---
id: T-0783
title: 'gates: long-deferred-obligation rule -- shipped deferral comment citing a
  still-open ticket past a release boundary'
state: done
kind: feature
origin: auditor
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- docs/design/registry/check-coverage.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: 'Adding TODO003 as a new gate rule requires registering it in the gate-rule

    registry (REG010: "1 live gate rule(s) have no CHK-GATE-<rule> entry");

    frob registry audit --sync-gate-rules is the sanctioned tool for this and

    necessarily touches docs/design/registry/check-coverage.yaml. This is

    mechanical glue required by the new gate rule itself, not a feature-scope

    expansion.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_gates.py::TestCoverageGate::test_todo003_fires_after_version_bump_since_deferral_landed
- tests/test_gates.py::TestCoverageGate::test_todo003_silent_when_no_version_bump_since_deferral
- tests/test_gates.py::TestCoverageGate::test_todo003_silent_when_ticket_closes
designated_repro_test: null
acceptance:
- text: GIVEN a shipped comment deferring work to ticket T-X (that ticket's job shape
    or frob:todo) WHEN T-X remains open across a REL001 version bump since the comment
    landed THEN a warning fires naming the deferral site and age; GIVEN the ticket
    closes THEN the finding clears
  evidence:
  - tests/test_gates.py::TestCoverageGate::test_todo003_fires_after_version_bump_since_deferral_landed
  - tests/test_gates.py::TestCoverageGate::test_todo003_silent_when_no_version_bump_since_deferral
  - tests/test_gates.py::TestCoverageGate::test_todo003_silent_when_ticket_closes
threat: null
component: null
---
Audit M2 gate-direction: deferred cleanup silently became permanent (T-0476 open since the lease layer shipped). Detect deferral comments bound to open tickets that have crossed release boundaries so deferrals get re-litigated instead of fossilizing.