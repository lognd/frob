---
id: T-0715
title: 'ticket organization model: epic -> story -> ticket tiers, sprint grouping,
  and team views'
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/ticket_runner.py
- docs/modules/tickets.md
- src/frob/__main__.py
- src/frob/app/config.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/__main__.py
  reason: ticket's own compound acceptance criterion requires the sprint/tier CLI
    surface (frob ticket new --tier, sprint assign/show); folding CLI in per coordinator
    direction instead of splitting the criterion
  actor: logan
  at: '2026-07-26'
- op: add
  glob: src/frob/app/config.py
  reason: ticket's own compound acceptance criterion requires the sprint/tier CLI
    surface (frob ticket new --tier, sprint assign/show); folding CLI in per coordinator
    direction instead of splitting the criterion
  actor: logan
  at: '2026-07-26'
- op: add
  glob: src/frob/app/ticket_runner.py
  reason: ticket's own compound acceptance criterion requires the sprint/tier CLI
    surface (frob ticket new --tier, sprint assign/show); folding CLI in per coordinator
    direction instead of splitting the criterion
  actor: logan
  at: '2026-07-26'
evidence:
- tests/test_tickets_tiers.py::TestTierField::test_default_tier_is_ticket
- tests/test_tickets_tiers.py::TestTierField::test_serialize_parse_round_trip
- tests/test_tickets_tiers.py::TestTierField::test_write_ticket_ledger_round_trip
- tests/test_tickets_tiers.py::TestTierField::test_new_ticket_carries_tier_and_sprint
- tests/test_tickets_tiers.py::TestDoableLeafOnly::test_epic_and_story_never_surface
- tests/test_tickets_tiers.py::TestCloseOpenDescendantGuard::test_epic_close_refused_with_open_descendant
- tests/test_tickets_tiers.py::TestCloseOpenDescendantGuard::test_epic_close_allowed_once_descendant_done
- tests/test_tickets_tiers.py::TestCloseOpenDescendantGuard::test_plain_ticket_close_unaffected_by_guard
- tests/test_tickets_tiers.py::TestSprintAssign::test_updates_sprint_field
- tests/test_tickets_tiers.py::TestSprintAssign::test_clears_to_none
- tests/test_tickets_tiers.py::TestSprintShow::test_state_rollup_and_velocity
- tests/test_tickets_tiers.py::TestSprintShow::test_no_tickets_in_sprint_is_empty_not_a_crash
- tests/unit/test_app_runners_t0715_sprint_tier.py::TestTicketNewTierSprint::test_new_carries_tier_and_sprint
- tests/unit/test_app_runners_t0715_sprint_tier.py::TestTicketDoableSprintByParent::test_doable_sprint_filter
- tests/unit/test_app_runners_t0715_sprint_tier.py::TestTicketDoableSprintByParent::test_doable_by_parent_groups_leaves
- tests/unit/test_app_runners_t0715_sprint_tier.py::TestTicketSprintAssignShow::test_assign_then_show
- tests/unit/test_app_runners_t0715_sprint_tier.py::TestTicketSprintAssignShow::test_show_json_mode
designated_repro_test: null
acceptance:
- text: GIVEN an epic with two stories each with open leaf tickets WHEN frob ticket
    doable runs THEN only leaves surface and closing the epic is refused while descendants
    are open; GIVEN tickets assigned to sprint-1 WHEN frob ticket sprint show sprint-1
    runs THEN the commitment lists with state rollup and closed-count velocity
  evidence:
  - tests/test_tickets_tiers.py::TestDoableLeafOnly::test_epic_and_story_never_surface
  - tests/test_tickets_tiers.py::TestCloseOpenDescendantGuard::test_epic_close_refused_with_open_descendant
  - tests/test_tickets_tiers.py::TestSprintAssign::test_updates_sprint_field
  - tests/test_tickets_tiers.py::TestSprintAssign::test_clears_to_none
  - tests/test_tickets_tiers.py::TestSprintShow::test_state_rollup_and_velocity
  - tests/test_tickets_tiers.py::TestSprintShow::test_no_tickets_in_sprint_is_empty_not_a_crash
  - tests/unit/test_app_runners_t0715_sprint_tier.py::TestTicketNewTierSprint::test_new_carries_tier_and_sprint
  - tests/unit/test_app_runners_t0715_sprint_tier.py::TestTicketDoableSprintByParent::test_doable_sprint_filter
  - tests/unit/test_app_runners_t0715_sprint_tier.py::TestTicketDoableSprintByParent::test_doable_by_parent_groups_leaves
  - tests/unit/test_app_runners_t0715_sprint_tier.py::TestTicketSprintAssignShow::test_assign_then_show
  - tests/unit/test_app_runners_t0715_sprint_tier.py::TestTicketSprintAssignShow::test_show_json_mode
threat: null
component: null
---
User mandate 2026-07-22 (first filing -- nothing like this existed in the ledger): formalize dev-team organization on top of the existing parent/blocked_by graph. (1) TIERS: an explicit tier field (epic|story|ticket, default ticket) with structural rules -- epics parent stories, stories parent tickets, doable only ever surfaces leaf tickets, an epic/story cannot close while an open descendant exists (today's convention, enforced); migration: existing EPIC-titled tickets get tier epic mechanically. (2) SPRINTS: a sprint field (free-form label like 2026-W30 or sprint-14) settable at new/via frob ticket sprint assign; frob ticket sprint show SPRINT lists committed tickets with state rollup; frob ticket doable --sprint SPRINT restricts the queue to the commitment; velocity/burndown derived from ledger state-transition history (closed-per-sprint counts), no new storage. (3) TEAM VIEWS: doable already orders by priority/age -- add --by-parent grouping so a story's remaining leaves display together (the user's pop-the-whole-stack-not-just-the-top concern). Keep the ledger format backward compatible (absent fields default); single-writer CLI discipline throughout. Coordinate with T-0571 (review records) and T-0573 (fleet routing) -- sprint labels should be routable cross-repo via fleet in a follow-up, note it, do not build it here.