---
id: T-3546
title: Land splice publishes tests-first then implementation instead of one squash
  (design vs T-3053)
state: queued
kind: feature
origin: human
created: '2026-08-31'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_squash.py
- src/frob/tickets/_land.py
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
Land currently squashes a ticket's whole worktree branch into ONE commit,
deliberately (the repro check is pre-land only because no ref holds
test-without-fix). Owner's bar: substantial, readable history -- ideally
TESTS-FIRST then IMPLEMENTATION, then any maintenance. Design and ship a
land splice that publishes a ticket as an ordered 2-3 commit shape:
  1. test(<scope>): the ticket's new/changed tests (red at this commit by
     construction where a genuine repro exists),
  2. feat/fix(<scope>): the implementation turning them green,
  3. (optional) chore: ledger/doc residue.
Consequences to handle explicitly: `--check-repro` becomes verifiable
POST-land from refs (upgrade it); bisect landing on commit 1 sees failing
tests -- decide and document the bisect story (e.g. `git bisect skip`
guidance or a commit trailer marking the pair); CI on main only runs on
the final push, so intermediate red commits never run CI. Design against
T-3053's compose-out-of-tree model. If a ticket's diff cannot be split
mechanically (no clean test/impl separation), fall back to today's single
squash -- never force a fabricated split.
