---
id: T-3620
title: 'gitio: commitless repo rev-parse HEAD surfaces as opaque interrupted'
state: queued
kind: bug
origin: human
created: '2026-08-31'
priority: low
parent: T-3505
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: v0.531.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gitio.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: parent
  old_value: null
  new_value: T-3505
  reason: 'pass2 backlog org: theme bucket ci-windows'
  actor: logan
  at: '2026-09-11'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-3619 (windows CI diag round 9). A repo that is
git init with zero commits makes frob's gitio helper's git rev-parse
--abbrev-ref HEAD fail rc=128 ("fatal: ambiguous argument 'HEAD':
unknown revision or path not in the working tree"). This currently
surfaces to the top-level CLI as a generic "frob: interrupted" (an
rc-coupled abort), not a clear message naming the actual condition
(no commits yet).

T-3619 fixed the CI fixture to always have a commit, so the CI symptom
is gone, but the underlying gitio behavior is still reachable by any
caller (a fresh git init with no commits, e.g. a real first-time user
running frob in a brand new repo before their first commit).

Suggest: gitio.py's rev-parse-HEAD helper(s) should distinguish
"no commits yet" (rc=128, "unknown revision") from other git failures
and raise/return a clear NoCommitsYet-shaped error instead of letting
the generic interrupted-abort path swallow it.
