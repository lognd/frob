---
id: T-5133
title: 'Sprint is a time box, milestone is the version: migrate v0.NNN.0 sprint labels
  into milestone, normalize the v prefix, re-slice the queue into weekly sprints'
state: done
kind: feature
origin: human
created: '2026-09-20'
priority: high
parent: null
tier: story
sprint: null
runs_last: false
milestone: 1.0.0
flavour: user_story
due: null
rank: null
points: null
unsized_ack: true
unsized_ack_reason: sizing verb CLI still broken pending T-5280/T-4702 land; ack recorded
  via library call
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5133
branch: t-5133
scope:
- src/frob/tickets/_sprint.py
- src/frob/tickets/_setters.py
- src/frob/app/ticket_runner/_mutate.py
- docs/commands/ticket.md
- docs/modules/tickets-data-storage.md
- src/frob/tickets/_new_renumber.py
- src/frob/tickets/_models.py
- src/frob/_cli_parsers/_ticket/_new.py
- src/frob/_cli_parsers/_ticket/_metadata.py
- src/frob/app/ticket_runner/_new.py
scope_breadth_ack: true
scope_breadth_ack_reason: sprint verb, setter validation, docs; plus a one-shot ledger
  migration run from the root
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_new_renumber.py
  reason: validate_sprint/sprint_shape_warning live in _models.py; TicketSpec.sprint
    validation at filing time lives in _new_renumber.py's gauntlet; --semver-sprint-ack
    CLI wiring for new/sprint-assign lives in _cli_parsers/_ticket
  actor: logan
  at: '2026-09-22'
- op: add
  glob: src/frob/tickets/_models.py
  reason: validate_sprint/sprint_shape_warning live in _models.py; TicketSpec.sprint
    validation at filing time lives in _new_renumber.py's gauntlet; --semver-sprint-ack
    CLI wiring for new/sprint-assign lives in _cli_parsers/_ticket
  actor: logan
  at: '2026-09-22'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_new.py
  reason: validate_sprint/sprint_shape_warning live in _models.py; TicketSpec.sprint
    validation at filing time lives in _new_renumber.py's gauntlet; --semver-sprint-ack
    CLI wiring for new/sprint-assign lives in _cli_parsers/_ticket
  actor: logan
  at: '2026-09-22'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_metadata.py
  reason: validate_sprint/sprint_shape_warning live in _models.py; TicketSpec.sprint
    validation at filing time lives in _new_renumber.py's gauntlet; --semver-sprint-ack
    CLI wiring for new/sprint-assign lives in _cli_parsers/_ticket
  actor: logan
  at: '2026-09-22'
- op: add
  glob: src/frob/app/ticket_runner/_new.py
  reason: --semver-sprint-ack CLI flag threading through new_ticket() call site
  actor: logan
  at: '2026-09-22'
triage_changes:
- field: milestone
  old_value: null
  new_value: 1.0.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-20'
- field: flavour
  old_value: null
  new_value: user_story
  reason: 'E2 (T-5766): census-based flavour classification (heuristic per E1''s own
    candidate signal)'
  actor: logan
  at: '2026-09-24'
body_changes:
- mode: append
  reason: 'owner directive 2026-09-20: sprint names are overarching goals, not versions
    and not week stamps'
  actor: logan
  at: '2026-09-20'
  old_length: 1455
  new_length: 2488
evidence:
- tests/test_tickets_sprint_migrate.py::TestValidateSprint::test_semver_shaped_refused
- tests/test_tickets_sprint_migrate.py::TestValidateSprint::test_calendar_shaped_warns_not_refuses
- tests/test_tickets_sprint_migrate.py::TestValidateSprint::test_goal_label_accepted
- tests/test_tickets_sprint_migrate.py::TestValidateSprint::test_semver_ack_bypasses_refusal
- tests/test_tickets_sprint_migrate.py::TestSprintShapeWarning::test_calendar_shaped_warns
- tests/test_tickets_sprint_migrate.py::TestSprintShapeWarning::test_goal_label_silent
- tests/test_tickets_sprint_migrate.py::TestMigrateSprintToMilestone::test_migrates_unmilestoned_ticket
- tests/test_tickets_sprint_migrate.py::TestMigrateSprintToMilestone::test_conflict_keeps_existing_milestone
- tests/test_tickets_sprint_migrate.py::TestMigrateSprintToMilestone::test_normalizes_v_prefixed_milestone
- tests/test_tickets_sprint_migrate.py::TestMigrateSprintToMilestone::test_idempotent_second_run_is_a_noop
- tests/test_tickets_sprint_migrate.py::TestBoardGroupsByMilestoneSemverOrder::test_board_orders_tickets_by_milestone_semver_not_lexical
designated_repro_test: null
acceptance:
- text: given the migrated ledger, when every open ticket is read, then no sprint
    value matches v?N.N.N and no milestone value starts with v
  evidence:
  - tests/test_tickets_sprint_migrate.py::TestValidateSprint::test_semver_shaped_refused
  - tests/test_tickets_sprint_migrate.py::TestValidateSprint::test_calendar_shaped_warns_not_refuses
  - tests/test_tickets_sprint_migrate.py::TestValidateSprint::test_goal_label_accepted
  - tests/test_tickets_sprint_migrate.py::TestValidateSprint::test_semver_ack_bypasses_refusal
  - tests/test_tickets_sprint_migrate.py::TestSprintShapeWarning::test_calendar_shaped_warns
  - tests/test_tickets_sprint_migrate.py::TestSprintShapeWarning::test_goal_label_silent
  - tests/test_tickets_sprint_migrate.py::TestMigrateSprintToMilestone::test_migrates_unmilestoned_ticket
  - tests/test_tickets_sprint_migrate.py::TestMigrateSprintToMilestone::test_conflict_keeps_existing_milestone
  - tests/test_tickets_sprint_migrate.py::TestMigrateSprintToMilestone::test_normalizes_v_prefixed_milestone
  - tests/test_tickets_sprint_migrate.py::TestMigrateSprintToMilestone::test_idempotent_second_run_is_a_noop
- text: given --sprint v0.560.0, when frob ticket new or sprint assign runs, then
    it refuses naming the milestone field as the right home
  evidence:
  - tests/test_tickets_sprint_migrate.py::TestValidateSprint::test_semver_shaped_refused
  - tests/test_tickets_sprint_migrate.py::TestValidateSprint::test_calendar_shaped_warns_not_refuses
  - tests/test_tickets_sprint_migrate.py::TestValidateSprint::test_goal_label_accepted
  - tests/test_tickets_sprint_migrate.py::TestValidateSprint::test_semver_ack_bypasses_refusal
  - tests/test_tickets_sprint_migrate.py::TestSprintShapeWarning::test_calendar_shaped_warns
  - tests/test_tickets_sprint_migrate.py::TestSprintShapeWarning::test_goal_label_silent
  - tests/test_tickets_sprint_migrate.py::TestMigrateSprintToMilestone::test_migrates_unmilestoned_ticket
  - tests/test_tickets_sprint_migrate.py::TestMigrateSprintToMilestone::test_conflict_keeps_existing_milestone
  - tests/test_tickets_sprint_migrate.py::TestMigrateSprintToMilestone::test_normalizes_v_prefixed_milestone
  - tests/test_tickets_sprint_migrate.py::TestMigrateSprintToMilestone::test_idempotent_second_run_is_a_noop
- text: given the re-sliced queue, when frob ticket sprint show 2026-W39 runs, then
    it lists the tickets, a state rollup and the milestones they belong to
  evidence:
  - tests/test_tickets_sprint_migrate.py::TestValidateSprint::test_semver_shaped_refused
  - tests/test_tickets_sprint_migrate.py::TestValidateSprint::test_calendar_shaped_warns_not_refuses
  - tests/test_tickets_sprint_migrate.py::TestValidateSprint::test_goal_label_accepted
  - tests/test_tickets_sprint_migrate.py::TestValidateSprint::test_semver_ack_bypasses_refusal
  - tests/test_tickets_sprint_migrate.py::TestSprintShapeWarning::test_calendar_shaped_warns
  - tests/test_tickets_sprint_migrate.py::TestSprintShapeWarning::test_goal_label_silent
  - tests/test_tickets_sprint_migrate.py::TestMigrateSprintToMilestone::test_migrates_unmilestoned_ticket
  - tests/test_tickets_sprint_migrate.py::TestMigrateSprintToMilestone::test_conflict_keeps_existing_milestone
  - tests/test_tickets_sprint_migrate.py::TestMigrateSprintToMilestone::test_normalizes_v_prefixed_milestone
  - tests/test_tickets_sprint_migrate.py::TestMigrateSprintToMilestone::test_idempotent_second_run_is_a_noop
- text: given the migration, when frob ticket board runs, then tickets group by milestone
    in semver order
  evidence:
  - tests/test_tickets_sprint_migrate.py::TestBoardGroupsByMilestoneSemverOrder::test_board_orders_tickets_by_milestone_semver_not_lexical
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
Owner directive 2026-09-20: sprint has been carrying the version (v0.533.0 .. v0.553.0 on 592 of 691 open tickets) while milestone is null on 398 and mixed-format on the rest (1.0.0 vs v0.541.0, 82 values still carry the v prefix validate_milestone now strips). The two fields have collapsed into one. Decision: milestone = the semver a ticket ships with (totally ordered, what ships together); sprint = a time box (when we work), smaller than one release so several milestones can close inside one sprint and a milestone can span sprints. Steps: (1) one-shot migration from the root: for every ticket whose sprint matches v?\d+\.\d+\.\d+, set milestone to that value (v stripped) when milestone is null, else keep the existing milestone and warn on conflict; then clear sprint; also normalize every existing v-prefixed milestone to bare semver; (2) validate_sprint refuses a semver-shaped label going forward (one override flag --semver-sprint-ack) so the collapse cannot recur; (3) re-slice open tickets into weekly sprints labelled YYYY-Www by milestone order and priority, sized against measured velocity (~20 lands/day over the last 7 days, ~29 over 21 days) and, once the sizing story lands, by points; (4) frob ticket sprint show and flow print both axes: per-sprint and per-milestone rollups; (5) update the one-minor-version-per-sprint directive in docs to one-or-more-milestones-per-sprint. Sizing story: see the ticket filed alongside this one.

AMENDMENT (owner, 2026-09-20): sprint labels are OVERARCHING GOALS, not version numbers and not calendar weeks. Step (3) changes: re-slice open tickets into goal-named sprints (kebab-case, e.g. csharp-unity, narrative-migration, kernel-decoupling, strata-friction, land-latency), one goal per sprint, each sized to roughly one to two weeks at measured velocity; the epic tree already names most goals, so the first pass maps each epic's sprint label from its parent epic's slug. Step (2) changes: validate_sprint refuses a semver-shaped label AND the refusal text suggests naming the goal ('a sprint is a goal you can say in three words; the version belongs in --milestone'); a label matching YYYY-Www or sprint-N gets a WARN with the same suggestion, not a refusal. frob ticket sprint show LABEL becomes the goal view: tickets, state rollup, milestones the goal spans, points and ETA. Acceptance amendment: the 2026-W39 criterion is replaced by frob ticket sprint show kernel-decoupling listing its tickets, rollup and milestones.