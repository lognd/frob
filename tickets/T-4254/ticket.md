---
id: T-4254
title: 'DRIFT/COV: symbols sharing one frob:doc anchor are one contract -- a ticket
  touching one should reopen review of all'
state: in-progress
kind: feature
origin: agent
created: '2026-09-07'
priority: high
parent: T-4182
tier: ticket
sprint: v1.1.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_docblocks_refs.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.538.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v0.538.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
acceptance:
- text: frob:doc edges sharing the same anchor are grouped into one contract (_shared_doc_anchor_groups),
    ignoring anchors with only one participant symbol
  evidence: []
- text: cov009_violations warns on every untouched sibling in a group once the diff
    touches at least one other sibling's own line span, and stays silent when the
    diff touches none or all of them
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer F-386 item 4 (T-4182, shell round-5): a shared contract's fix and its miss landed in two different tickets' scopes because frob has no notion that these call sites implement one contract; the frob:doc edges all point at the same anchor, which is the right hook -- a DRIFT/COV rule keyed on symbols sharing one frob:doc anchor could treat that anchor as a single obligation, so touching one participant flags the others for review. Adjacent to T-4252 (AFFECT-style sibling-signature check) -- distinct mechanism (this is anchor-based grouping across possibly-different files/shapes; T-4252 is same-module sibling-signature matching) but both close the same class of gap. Fixture-testable: YES, frob's own frob:doc anchors.