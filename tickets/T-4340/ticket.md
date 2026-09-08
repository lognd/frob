---
id: T-4340
title: Audit the remaining ~280 T-3844-promoted rules for waivability and structural
  silence
state: planned
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- frob.toml
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
T-4328 covered property 1 (contradictory documented severity) across all 308 T-3844-promoted rules via a source-docstring grep. T-4331 covered property 2 (waivability) and property 3 (structural silence) for the tickets/milestone/bug-repro cluster and a handful of shape-matched siblings (PORT001-PATH/DEFAULT, REL001, LEDGERV1001, MILE001-4, TICK013), demoting SCOPE002/TICK008/TICK005 and leaving the rest at error with a per-rule reason recorded in its Done report. Roughly 280 rules outside that cluster (PERF/SEC/PII/ARCH/DOC/REG/COMPLIANCE/KRB/DEPLOY/FFI/LANG/NATIVE/PROFILE/WAIVE/etc.) were not walked with the same rigor. Method (T-4331's Done report): for each remaining rule, find every rule=<ID> Violation-construction site and check whether line can be a real waiver-matchable source line or a hardcoded 0 against a path that may not exist (property 2), and check the containing function for a config/feature flag or a stale git-object/API read that would make it silently unreachable in this repo's current state (property 3, the TICK005/COV002-T-1582 shape: a v1-only git-object read never updated for a v2 layout migration). Do NOT mass-demote -- most are plausibly fine; report per-rule reasoning for anything left at error, same as T-4328/T-4331.