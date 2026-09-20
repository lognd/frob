---
id: T-draft-f24022de
title: delete the emptied design/frob.strata and every reference to it
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: critical
blocked_by:
- T-draft-ff65ecc5
parent: T-draft-0a0c7b43
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.536.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
acceptance:
- text: Given the repository after this land, when design/frob.strata is looked for,
    then it does not exist, and no code, config, doc or test references it.
  evidence: []
- text: 'Given the strata checker and the SYS gates, when they run, then they are
    green over the 11 per-module files alone -- positive control: a planted finding
    in one module file is still reported.'
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Delete design/frob.strata. By this point all 11 migration leaves have landed and
the monolith is empty (or holds only its header). Remove the file and every
reference to it in tooling and docs, so the design is the set of per-module
files and nothing silently keeps reading a 2766-line monolith that no longer
exists.
