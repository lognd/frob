---
id: T-1148
title: 'check: detect missing/stale strata_core+frob_core natives and fail honestly
  (or auto-build) instead of 43 bogus DRIFT002s'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/strata/**
- tests/test_gates.py
- tests/unit/strata/test_native_staleness.py
- docs/modules/gates.md
- frob.lock
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/test_native_staleness.py
  reason: unit tests for the new unimportable_natives/native_unavailable_warning helpers
    this ticket adds
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/gates.md
  reason: NATIVE001 gate needs a real docs/modules/gates.md anchor for its frob:doc
    directives (DOC002)
  actor: logan
  at: '2026-07-28'
- op: add
  glob: frob.lock
  reason: frob ack writes body/sig digests for run_gates here after its behavior changed
  actor: logan
  at: '2026-07-28'
- op: add
  glob: design/frob.strata
  reason: SYS104 mandatory sync-interface upkeep after adding public symbols in this
    ticket's scope
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_reports_a_declared_native_that_fails_to_import
- tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_healthy_native_reports_nothing
- tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_no_declared_natives_reports_nothing
- tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_warning_names_the_native_and_the_fix_command
- tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_warning_is_none_when_nothing_broken
- tests/test_gates.py::TestNativeAvailabilityGate::test_unimportable_native_short_circuits_run_gates_with_one_finding
- tests/test_gates.py::TestNativeAvailabilityGate::test_every_native_importable_runs_the_normal_pipeline
designated_repro_test: null
acceptance:
- text: GIVEN a checkout whose installed natives are missing or stale relative to
    the native source tree WHEN frob check runs any stage that needs them THEN it
    reports ONE actionable finding naming the cause and the fix command (frob natives
    build) -- or auto-builds under a config flag -- and never emits resolver no-candidates
    errors misattributed to design/doc drift
  evidence:
  - tests/test_gates.py::TestNativeAvailabilityGate::test_unimportable_native_short_circuits_run_gates_with_one_finding
threat: null
component: null
---
2026-07-28 incident: a root uv sync reinstalled frob without the natives; the next check produced 43 DRIFT002 'no candidates' errors against every design/frob.strata node -- misattributed, alarming, and fixed only by coordinator memory of the worktree-natives artifact (this also recurs in fresh worktrees and sibling repos per the estate rollout T-1031/T-1071 work). The elaboration path knows when strata_core failed to import or its build stamp trails the native source tree; surface THAT, once, with the fix command. Pairs with the T-0864 natives build subcommand and the T-1031 estate shim.