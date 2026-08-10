---
id: T-1940
title: Generalize T-1932's post-mutation guard re-check into a registry every future
  land-path guard is forced to use
state: done
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
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: T-1940's registry needs a structural completeness test asserting every committed-diff-reading
    land guard is registered with a twin or an explicit exemption reason
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_ticket_land.py::TestCommittedDiffGuardRegistryCompleteness::test_every_call_site_guard_is_registered
- tests/test_ticket_land.py::TestCommittedDiffGuardRegistryCompleteness::test_every_registry_entry_has_a_twin_or_a_stated_reason
- tests/test_ticket_land.py::TestCommittedDiffGuardRegistryCompleteness::test_registered_twins_are_actually_wired_into_the_land_sequence
designated_repro_test: tests/test_ticket_land.py::TestCommittedDiffGuardRegistryCompleteness::test_every_call_site_guard_is_registered
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