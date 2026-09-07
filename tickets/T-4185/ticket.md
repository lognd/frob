---
id: T-4185
title: 'SELFAUDIT: a via-glob matching zero files on the current branch is its own
  finding, not a suppressible unobserved capability'
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: high
parent: T-4109
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_sys_selfaudit.py
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
Consumer F-307/H3-10 (T-4109). A declared via-glob that matches no file on the current branch is accepted silently; SELFAUDIT001 reports only capability-unobserved, which the tree's own waivers then suppress. Extend the T-3985 zero-subject-count primitive to declaration globs: 'glob matches nothing' must be its own finding, distinct from 'capability unobserved'. Fixture-testable: YES, in frob's own tree (declare a via entry with a glob matching nothing). Consumer-blocking: yes, now -- this undermines every rule built on declarations, including several sibling leaves under T-4109/T-4157 that assume declarations are trustworthy.