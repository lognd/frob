---
id: T-3720
title: ROOT001 remedy prescribes frob:external-reader directive that DSL001 rejects
state: queued
kind: bug
origin: human
created: '2026-09-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_root_asset_dirs.py
- src/frob/graph/dsl.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/check/**
  reason: defect is in the remedy-text generator + dsl verb registries, not check/**
  actor: logan
  at: '2026-09-03'
- op: add
  glob: src/frob/gates/_root_asset_dirs.py
  reason: defect is in the remedy-text generator + dsl verb registries, not check/**
  actor: logan
  at: '2026-09-03'
- op: add
  glob: src/frob/graph/dsl.py
  reason: defect is in the remedy-text generator + dsl verb registries, not check/**
  actor: logan
  at: '2026-09-03'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
apollo FROBLEMS.md 2026-09-03: ROOT001's remedy text says to add <!-- frob:external-reader dir="..." reason="..." --> but doing so trips DSL001 'unhandled markdown directive (verb=external-reader): nothing reads it'. A gate remedy that another gate errors on is a trap; scaffold's .github/ and invariants/ ROOT001 warnings are therefore left standing with no clean remedy path. Related to T-3719 (scaffold self-conformance) -- same underlying trap, filed separately since the fix is in the check/DSL layer, not the scaffold templates.

## Failure log
- 2026-09-03 attempt 1: Declared scope src/frob/check/** does not contain the defect: ROOT001's remedy text lives in src/frob/gates/_root_asset_dirs.py (external-reader directive generation) and DSL001's unhandled-verb check is in src/frob/graph/dsl.py (verb registries _RESERVED_MARKER_VERBS/_ATTR_ONLY_VERBS). Nothing under src/frob/check/** references ROOT001, DSL001, or external-reader. Needs a ticket scoped to src/frob/gates/_root_asset_dirs.py and src/frob/graph/dsl.py instead.
