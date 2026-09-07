---
id: T-4232
title: 'strata: model a node''s runtime-mounted artifact set; check relative import/include
  targets in a config file resolve within it'
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: medium
parent: T-4135
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata
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
Consumer F-325/H2-1 (edge/ops round-2 sub-epic of T-4135): a config file (e.g. an edge server's include directive) references a mount path with no gate connecting the declared may fs.read grant to what a deployment's compose service actually mounts. Even without a config-file grammar, a path-set comparison between two text files frob already reads would catch this. Adjacent to T-3996 (required_file: declared surface for untracked-but-mandatory artifacts) -- distinct mechanism (mount-path resolution vs. untracked-mandatory-file declaration), cross-reference during design. Not fixture-testable in frob's own tree: no containers/mounts exist here.