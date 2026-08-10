---
id: T-1940
title: Generalize T-1932's post-mutation guard re-check into a registry every future
  land-path guard is forced to use
state: queued
kind: bug
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1932 established a worked pattern for making a land-path guard's
refusal survive a later mutation (self-delegating re-invocation of the
SAME check function, called after `_land_merge_stage`'s wip-commit,
pinned by a source-order introspection test) and applied it to
`_check_cross_ticket_leakage` (the T-1931 instance). It deliberately did
NOT build a generic, structural registry that forces every OTHER
committed-diff-reading guard in `_land_precheck_remaining_checks`
(`_check_passenger_tickets`, `_check_already_landed`, and any guard added
later) to register a post-mutation twin automatically -- each of those
currently relies on the same worked example being copied by hand, same as
before T-1932, just with a clearer template and a locked regression test
now proving the copy works.

Investigate and build a real registry: walk
`_land_precheck_remaining_checks`'s own guard list generically (or an
explicit `_COMMITTED_DIFF_GUARDS` tuple naming each check plus its
post-mutation twin), and add a test that fails if a NEW guard is added to
the preflight sequence without a corresponding registered post-mutation
re-check -- closing T-1932 acceptance criterion 4 mechanically for every
future guard, not just the one this ticket touched by hand.

Scope: src/frob/tickets/_land.py
