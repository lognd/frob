---
id: T-2957
title: 'frob-dup: burn the family to zero and promote WARN to ERROR (restores T-2378''s
  original commitment)'
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: high
parent: T-0969
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_setters.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_walk_lint.py
  reason: real de-duplication burn-down for T-2957 (frob-dup family), extracting shared
    helpers for same-file duplicate blocks
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: real de-duplication burn-down for T-2957 (frob-dup family), extracting shared
    helpers for same-file duplicate blocks
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: real de-duplication burn-down for T-2957 (frob-dup family), extracting shared
    helpers for same-file duplicate blocks
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/tickets/_setters.py
  reason: real de-duplication burn-down for T-2957 (frob-dup family), extracting shared
    helpers for same-file duplicate blocks
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/deploy/_generate_windows.py
  reason: real de-duplication burn-down for T-2957 (frob-dup family), extracting shared
    helpers for same-file duplicate blocks
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/strata/_mode_conformance.py
  reason: real de-duplication burn-down for T-2957 (frob-dup family), extracting shared
    helpers for same-file duplicate blocks
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/gates/_wire.py
  reason: real de-duplication burn-down for T-2957 (frob-dup family), extracting shared
    helpers for same-file duplicate blocks
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/lang/_walk_bash.py
  reason: real de-duplication burn-down for T-2957 (frob-dup family), extracting shared
    helpers for same-file duplicate blocks
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/tickets/_store.py
  reason: real de-duplication burn-down for T-2957 (frob-dup family), extracting shared
    helpers for same-file duplicate blocks
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/app/check_runner.py
  reason: real de-duplication burn-down for T-2957 (frob-dup family), extracting shared
    helpers for same-file duplicate blocks
  actor: logan
  at: '2026-08-30'
- op: remove
  glob: src/frob/gates/_walk_lint.py
  reason: narrowed to the one genuine extraction actually implemented (set_priority/set_tier/set_component
    reason-guard de-dup); rest of the frob-dup family deferred to a follow-up triage
    ticket
  actor: logan
  at: '2026-08-30'
- op: remove
  glob: src/frob/tickets/_land_git_ops.py
  reason: narrowed to the one genuine extraction actually implemented (set_priority/set_tier/set_component
    reason-guard de-dup); rest of the frob-dup family deferred to a follow-up triage
    ticket
  actor: logan
  at: '2026-08-30'
- op: remove
  glob: src/frob/_cli_parsers/_misc.py
  reason: narrowed to the one genuine extraction actually implemented (set_priority/set_tier/set_component
    reason-guard de-dup); rest of the frob-dup family deferred to a follow-up triage
    ticket
  actor: logan
  at: '2026-08-30'
- op: remove
  glob: src/frob/deploy/_generate_windows.py
  reason: narrowed to the one genuine extraction actually implemented (set_priority/set_tier/set_component
    reason-guard de-dup); rest of the frob-dup family deferred to a follow-up triage
    ticket
  actor: logan
  at: '2026-08-30'
- op: remove
  glob: src/frob/strata/_mode_conformance.py
  reason: narrowed to the one genuine extraction actually implemented (set_priority/set_tier/set_component
    reason-guard de-dup); rest of the frob-dup family deferred to a follow-up triage
    ticket
  actor: logan
  at: '2026-08-30'
- op: remove
  glob: src/frob/gates/_wire.py
  reason: narrowed to the one genuine extraction actually implemented (set_priority/set_tier/set_component
    reason-guard de-dup); rest of the frob-dup family deferred to a follow-up triage
    ticket
  actor: logan
  at: '2026-08-30'
- op: remove
  glob: src/frob/lang/_walk_bash.py
  reason: narrowed to the one genuine extraction actually implemented (set_priority/set_tier/set_component
    reason-guard de-dup); rest of the frob-dup family deferred to a follow-up triage
    ticket
  actor: logan
  at: '2026-08-30'
- op: remove
  glob: src/frob/tickets/_store.py
  reason: narrowed to the one genuine extraction actually implemented (set_priority/set_tier/set_component
    reason-guard de-dup); rest of the frob-dup family deferred to a follow-up triage
    ticket
  actor: logan
  at: '2026-08-30'
- op: remove
  glob: src/frob/app/check_runner.py
  reason: narrowed to the one genuine extraction actually implemented (set_priority/set_tier/set_component
    reason-guard de-dup); rest of the frob-dup family deferred to a follow-up triage
    ticket
  actor: logan
  at: '2026-08-30'
triage_changes:
- field: parent
  old_value: null
  new_value: T-0969
  reason: T-2378 was marked done after amending its acceptance criteria from burn-to-zero-and-promote
    down to the single pair it fixed (1 of 557 findings); T-2957 restores the original
    commitment and is gated on the two triage children
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
