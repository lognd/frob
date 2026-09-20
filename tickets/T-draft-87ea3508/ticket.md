---
id: T-draft-87ea3508
title: 'Sprint is a time box, milestone is the version: migrate v0.NNN.0 sprint labels
  into milestone, normalize the v prefix, re-slice the queue into weekly sprints'
state: queued
kind: feature
origin: human
created: '2026-09-20'
priority: high
parent: null
tier: story
sprint: v0.534.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_sprint.py
- src/frob/tickets/_setters.py
- src/frob/app/ticket_runner/_mutate.py
- docs/commands/ticket.md
- docs/modules/tickets-data-storage.md
scope_breadth_ack: true
scope_breadth_ack_reason: sprint verb, setter validation, docs; plus a one-shot ledger
  migration run from the root
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given the migrated ledger, when every open ticket is read, then no sprint
    value matches v?N.N.N and no milestone value starts with v
  evidence: []
- text: given --sprint v0.560.0, when frob ticket new or sprint assign runs, then
    it refuses naming the milestone field as the right home
  evidence: []
- text: given the re-sliced queue, when frob ticket sprint show 2026-W39 runs, then
    it lists the tickets, a state rollup and the milestones they belong to
  evidence: []
- text: given the migration, when frob ticket board runs, then tickets group by milestone
    in semver order
  evidence: []
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
Owner directive 2026-09-20: sprint has been carrying the version (v0.533.0 .. v0.553.0 on 592 of 691 open tickets) while milestone is null on 398 and mixed-format on the rest (1.0.0 vs v0.541.0, 82 values still carry the v prefix validate_milestone now strips). The two fields have collapsed into one. Decision: milestone = the semver a ticket ships with (totally ordered, what ships together); sprint = a time box (when we work), smaller than one release so several milestones can close inside one sprint and a milestone can span sprints. Steps: (1) one-shot migration from the root: for every ticket whose sprint matches v?\d+\.\d+\.\d+, set milestone to that value (v stripped) when milestone is null, else keep the existing milestone and warn on conflict; then clear sprint; also normalize every existing v-prefixed milestone to bare semver; (2) validate_sprint refuses a semver-shaped label going forward (one override flag --semver-sprint-ack) so the collapse cannot recur; (3) re-slice open tickets into weekly sprints labelled YYYY-Www by milestone order and priority, sized against measured velocity (~20 lands/day over the last 7 days, ~29 over 21 days) and, once the sizing story lands, by points; (4) frob ticket sprint show and flow print both axes: per-sprint and per-milestone rollups; (5) update the one-minor-version-per-sprint directive in docs to one-or-more-milestones-per-sprint. Sizing story: see the ticket filed alongside this one.