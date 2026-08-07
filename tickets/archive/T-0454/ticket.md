---
id: T-0454
title: 'EPIC: professional ticket organization -- sprints/milestones, epic->story->task
  rollup, components/labels, priority-ordered board (frob ticket board/sprint/epic),
  no ceremony'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/
- src/frob/app/ticket_runner.py
- src/frob/__main__.py
- docs/
- tests/unit/test_ticket_store.py
- tests/test_tickets_organization.py
- src/frob/gates/__init__.py
- src/frob/graph/dsl.py
- tests/test_gates.py
- tests/unit/graph/test_dsl.py
- pyproject.toml
- CHANGELOG.md
- .frob-release.json
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: T-0454 tickets work maps to tests/unit/test_ticket_store.py
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_tickets_organization.py
  reason: T-0454 new component/labels/board/epic surface needs its own test file,
    mirroring T-0411's test_tickets_priority.py precedent
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'sequential single-worktree dispatch: T-0527''s committed files still show
    in the diff-vs-main SCOPE001 check for T-0454 (T-0108/T-0412/T-0527 precedent)
    since those commit subjects did not carry a T-0527 reference'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/graph/dsl.py
  reason: 'sequential single-worktree dispatch: T-0526/T-0527''s committed files still
    show in the diff-vs-main SCOPE001 check for T-0454 (T-0108/T-0412/T-0527 precedent)'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_gates.py
  reason: 'sequential single-worktree dispatch: T-0527''s committed test file still
    shows in the diff-vs-main SCOPE001 check for T-0454 (T-0108/T-0412/T-0527 precedent)'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/graph/test_dsl.py
  reason: 'sequential single-worktree dispatch: T-0526''s committed test file still
    shows in the diff-vs-main SCOPE001 check for T-0454 (T-0108/T-0412/T-0527 precedent)'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: T-0454's own REL001 minor version bump (new public component/labels/board_view/epic_rollup/set_component/mutate_labels
    API)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: T-0454's own REL001 minor version bump (new public component/labels/board_view/epic_rollup/set_component/mutate_labels
    API)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: T-0454's own REL001 minor version bump (new public component/labels/board_view/epic_rollup/set_component/mutate_labels
    API)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: T-0454's own REL001 minor version bump (new public component/labels/board_view/epic_rollup/set_component/mutate_labels
    API)
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_tickets_organization.py::TestFieldRoundTrip::test_serialize_parse_round_trip
- tests/test_tickets_organization.py::TestFieldRoundTrip::test_write_ticket_ledger_round_trip
- tests/test_tickets_organization.py::TestFieldRoundTrip::test_comma_joined_label_splits
- tests/test_tickets_organization.py::TestFieldRoundTrip::test_new_ticket_carries_component_and_labels
- tests/test_tickets_organization.py::TestSetComponent::test_updates_component_field
- tests/test_tickets_organization.py::TestSetComponent::test_clears_to_none
- tests/test_tickets_organization.py::TestMutateLabels::test_add_and_remove_labels
- tests/test_tickets_organization.py::TestMutateLabels::test_empty_call_is_error
- tests/test_tickets_organization.py::TestBoardView::test_columns_in_fixed_order
- tests/test_tickets_organization.py::TestBoardView::test_priority_ordered_within_column
- tests/test_tickets_organization.py::TestBoardView::test_component_filter
- tests/test_tickets_organization.py::TestBoardView::test_label_filter
- tests/test_tickets_organization.py::TestEpicRollup::test_not_found_is_err
- tests/test_tickets_organization.py::TestEpicRollup::test_counts_done_and_total
- tests/test_tickets_organization.py::TestEpicRollup::test_blocked_leaf_surfaced
- tests/test_tickets_organization.py::TestEpicRollup::test_childless_epic_is_zero_percent_not_a_crash
- tests/unit/test_ticket_store.py::TestLoadAllAndWriteTicket::test_component_and_labels_round_trip
designated_repro_test: null
threat: null
component: null
---
User request 2026-07-20: the ticket queue is a flat list with occasional
epics; the user wants a professional dev-team workflow (no ceremony/standups,
but real organization). This is the "hierarchically catalogue features"
mandate from CLAUDE.md made concrete.

Design (organization on top of the flat ledger, additive fields + views):
- Hierarchy: epic -> story -> task via the existing `parent` field made
  first-class. `frob ticket epic T-####` shows the whole subtree with a
  rollup (N done / M total, % complete, blocked leaves). An epic with no
  children warns; a leaf's parent chain should terminate at an epic.
- Sprints/milestones: a `sprint`/`milestone` field (id + goal + optional
  date window). `frob ticket sprint new/list/show/assign`; a ticket in at
  most one active sprint. `frob ticket sprint show S-##` = the sprint
  backlog with per-ticket state.
- Components/labels: a `component` (module area: gates, strata, dup, vet,
  deploy, render, tickets, ...) + freeform `labels`. doable/board filter by
  component so a coordinator drains one area at a time.
- Priority: an ordered priority field feeding doable's ordering (today
  oldest-first only) so critical-path work surfaces first, still respecting
  blocks + the T-0453 lease filter.
- Board view: `frob ticket board` renders columns by state (backlog/queued
  -> in-progress -> review -> done), optionally scoped to a sprint/component,
  through the T-0448 output layer (pretty TTY, plain for agents).
- Additive to the git-tracked ledger; the T-0323 merge driver must splice
  the new fields; every field optional so existing tickets stay valid.
- Relates: T-0453 (collision-aware doable/lease) is the scheduling half,
  this is the organization half. File child tickets per capability under
  this epic (dogfood the hierarchy).