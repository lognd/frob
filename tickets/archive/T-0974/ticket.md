---
id: T-0974
title: 'Enable [dup].enforce=true by default: profile/cache find_clones to fit the
  check budget'
state: done
kind: bug
origin: auditor
created: '2026-07-27'
priority: medium
blocked_by:
- T-0981
- T-0982
parent: T-0969
tier: ticket
sprint: null
scope:
- src/frob/dup/**
- src/frob/gates/__init__.py
- frob.toml
- docs/modules/dup.md
- tests/test_dup_native_rungs.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/dup.md
  reason: documenting new DupConfig.native_rungs_enabled / [dup].native_rungs config
    knob added to fit the check budget
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/test_dup_native_rungs.py
  reason: new regression test for DupConfig.native_rungs_enabled added by this ticket
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/gates.md
  reason: 'AFFECT001: dup_gate''s affects()-closure doc must be touched alongside
    its native_rungs signature change'
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_dup_native_rungs.py::TestNativeRungsDefaultsOnForDirectCallers::test_default_config_still_reports_native_rungs
- tests/test_dup_native_rungs.py::TestNativeRungsOffWhenDisabled::test_explicit_false_reports_no_native_rungs
- tests/test_dup_native_rungs.py::TestNativeRungsEnabled::test_enabled_finds_the_r4_gapped_clone
- tests/test_dup_native_rungs.py::TestNativeRungsEnabled::test_enabled_finds_the_r5_dataflow_clone
- tests/test_gates.py::TestOptInGates::test_dup_gate_off_by_default
- tests/test_gates.py::TestOptInGates::test_dup_gate_fires_on_planted_clone_when_enabled
- tests/test_gates.py::TestOptInGates::test_dup_gate_fails_closed_when_enforced_but_core_missing
designated_repro_test: null
threat: null
component: null
---
gates-quality audit (T-0399) finding 2: DUP is off by default (no [dup]
block in this repo's frob.toml) and, before T-0399, silently no-op'd if
[dup].enforce=true but frob-core was missing. T-0399 fixed the fail-open
half: dup_gate now emits DUP003 (ERROR) when enforce=true but frob-core is
unavailable (src/frob/gates/__init__.py::dup_gate). This ticket is the
remaining half: turning [dup].enforce=true ON for this repo.

T-0399 tried a live trial of enforce=true and it made a single
`gates-native` --only chunk run past this repo's own ~150s foreground
budget (docs/guides/agent-playbook.md section 3b), even though DUP001/
DUP002 only ever REPORT on diff-touched refs -- `find_clones` builds its
clone index over the WHOLE snapshot first, so the cost is not diff-scoped
the way the reported violations are.

Plan: (a) profile `find_clones`/the R1-R5 pipeline to find the actual
whole-snapshot cost driver; (b) either cache the snapshot-wide index
incrementally (keyed off content hashes, invalidated only for
changed files) or narrow what gets indexed by default (e.g. skip R3-R5
native rungs unless a config flag opts in, keep R1/R2 pure-Python on by
default since those are cheap) so a full gate pass stays inside the
foreground budget; (c) once affordable, set [dup].enforce = true in this
repo's own frob.toml and re-verify a full chunked `frob check` stays
inside budget before closing.