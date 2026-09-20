---
id: T-4716
title: Gate registry owns each rule's one-sentence description; DOCENUM002 flags mismatched/unregistered
  docs table rows
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4661
parent: T-4655
tier: ticket
sprint: v0.535.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_registry.py
- docs/modules/gate-registration.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: parent
  old_value: null
  new_value: T-4655
  reason: 'T-3032 dispatch: DOCENUM002 lint follow-up belongs under the GATES story
    alongside T-4661'
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: null
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured (owner, via coordinator): docs/modules/vet.md rows VET006/VET008/VET009/VET010 (written 2026-07-17 as a design wish-list) contradict docs/modules/gates.md and the emitting sites in src/frob/vet/_supplychain.py (implemented 2026-08-06 under T-1088). Nothing caught it because rule ids are bare rule="VET008" literals with no attached description, DOCENUM001 only checks id existence in gates.md, and vet.md's table is unbound. Fix: (1) frob.gates._registry.GateRegistration carries each rule's one-sentence human description and severity; gates.md's rule-table row becomes DERIVED from it (one of T-4661's four derived views already -- extend it so the row TEXT, not just the id, is derived). (2) Add a lint (DOCENUM002, or the id the doctrine assigns) scanning every markdown table row shaped '| <RULE-ID> | ... |' under docs/: flag a row whose id is registered but whose text does not match the registered description, and a row whose id is NOT registered at all (a wish-list row wearing a live-looking id). POSITIVE CONTROL: the current vet.md VET006/008/009/010 rows must fire until a docs agent fixes them (a separate ticket already owns that docs fix, filed ~18:20). Scope is deliberately narrow: the registry's description field, the new lint module, its tests, and docs/modules/gate-registration.md only -- does NOT touch docs/modules/vet.md or docs/modules/gates.md (both leased/owned elsewhere).