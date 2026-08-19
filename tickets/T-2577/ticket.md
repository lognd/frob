---
id: T-2577
title: 'M3: milestone as primary doable sort axis, inheritance, --milestone filter'
state: done
kind: feature
origin: human
created: '2026-08-18'
priority: high
blocked_by:
- T-2574
parent: T-2573
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- src/frob/tickets/_doable.py
- src/frob/tickets/__init__.py
- src/frob/app/ticket_runner/_query.py
- src/frob/_cli_parsers/_ticket/_query.py
- src/frob/app/_config_external.py
- docs/modules/tickets.md
- docs/modules/tickets-data-storage.md
- tests/test_tickets_milestone_sort.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_ticket/_query.py
  reason: '--milestone doable filter is part of T-2577''s own acceptance (constraint
    1);

    CLI wiring for it lives in the argparse registration and the external-config

    allowlist, mirroring the existing --sprint flag pattern (ticket_doable_sprint).

    '
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/app/_config_external.py
  reason: '--milestone doable filter is part of T-2577''s own acceptance (constraint
    1);

    CLI wiring for it lives in the argparse registration and the external-config

    allowlist, mirroring the existing --sprint flag pattern (ticket_doable_sprint).

    '
  actor: logan
  at: '2026-08-19'
- op: add
  glob: docs/modules/tickets.md
  reason: '_doable_sort_key doc-closure target; documenting the milestone-primary

    ordering change in the same module doc T-2574 already anchored.

    '
  actor: logan
  at: '2026-08-19'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: '_doable_sort_key doc-closure target; documenting the milestone-primary

    ordering change in the same module doc T-2574 already anchored.

    '
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tests/test_tickets_milestone_sort.py
  reason: 'New test file bound as evidence for T-2577''s own acceptance

    (effective_milestone/_doable_sort_key milestone-primary ordering).

    '
  actor: logan
  at: '2026-08-19'
evidence:
- tests/test_tickets_milestone_sort.py::TestEffectiveMilestone::test_own_milestone_is_declared
- tests/test_tickets_milestone_sort.py::TestEffectiveMilestone::test_inherits_from_parent_story
- tests/test_tickets_milestone_sort.py::TestEffectiveMilestone::test_inherits_from_grandparent_epic
- tests/test_tickets_milestone_sort.py::TestEffectiveMilestone::test_nearest_ancestor_wins_over_farther_one
- tests/test_tickets_milestone_sort.py::TestEffectiveMilestone::test_no_milestone_anywhere_in_chain_is_none
- tests/test_tickets_milestone_sort.py::TestEffectiveMilestone::test_cycle_does_not_infinite_loop
- tests/test_tickets_milestone_sort.py::TestDoableSortKey::test_earlier_milestone_outranks_critical_later_milestone
- tests/test_tickets_milestone_sort.py::TestDoableSortKey::test_later_milestone_still_appears_sorted_last_never_absent
- tests/test_tickets_milestone_sort.py::TestDoableSortKey::test_unmilestoned_sorts_after_every_declared_milestone
- tests/test_tickets_milestone_sort.py::TestDoableSortKey::test_semver_numeric_not_lexical_ordering
- tests/test_tickets_milestone_sort.py::TestDoableSortKey::test_no_queue_falls_back_to_own_milestone_only
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Three parts:

1. Milestone becomes the PRIMARY sort axis in `_doable_sort_key`
   (src/frob/tickets/__init__.py), ahead of priority. Current key is
   exactly `(-PRIORITY_RANK[t.priority], t.created, t.id)` (verified
   2026-08-18) -- milestone must sort BEFORE that tuple, so a critical
   v1.1 ticket never outranks a low v1.0 ticket while 1.0 is shipping.

2. Later-milestone tickets are SORTED LAST, NEVER HIDDEN from
   `_doable_candidates`/doable output -- hiding work is a silent zero.
   Add a `--milestone` FILTER flag for when the operator explicitly wants
   just one milestone.

3. Effective milestone = own if set, else nearest ancestor's (epic or
   story). `doable` output must SHOW the effective milestone AND whether
   it was inherited or declared -- an inherited value must never be
   indistinguishable from a declared one in the rendered output.

Depends on M1 (T-2574, field must exist) and M2 (T-2576, MILE003 backfill
-- without it every open ticket sorts as unmilestoned and the ordering
change is untestable against real data).

Explicitly out of scope: MILE00x gates (M4/M4b/M5), REL001 (M6).