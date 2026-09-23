---
id: T-4233
title: 'frob:invariant: flag a component whose only bound tests exercise one happy-path
  fixture value for a parameter-shaped input'
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: medium
parent: T-4135
tier: ticket
sprint: null
runs_last: false
milestone: 1.1.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_inv.py
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
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer F-325/H2-2 first half: a credential-parsing invariant had no evidence to bind to because the only bound test used a password with no reserved characters -- 'no bound test varies input X' is checkable from the test source for parameter-shaped inputs. Adjacent to T-3997 (TESTMOCK001: fully-mocked subjects need a non-mocked companion) -- same family (a test that LOOKS like coverage but structurally cannot exercise the failure mode) but a distinct trigger (single-fixture-value vs full-mock). Fixture-testable: YES, generically, with a synthetic parameterized function in frob's own tree.