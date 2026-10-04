+++
id = "01M3AXSDBEQGV8V5VHYGXBEQTV"
title = "strata expressiveness: model any scaled system"
type = "story"
category = "todo"
priority = "low"
parent = "01M3AXSDACKS00T3E853M1J0DR"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T22:22:26Z"
aliases = ["T-6510"]
labels = ["v1-cluster:B1", "area:grimble", "triage:accepted", "milestone:0.538.0"]
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: strata expressiveness: model any scaled system
kind: feature
tier: story
parent: T-SYS-EPIC
milestone: 0.539.0
sprint: sysdesign
scope: (none -- story, no direct code scope)
blocked_by: []

Body:

Leaves in this story come from STRATA-EXPRESSIVENESS.md's GRAMMAR proposals only (RULE-ONLY
proposals from the same audit are filed as rule leaves in Stories C-G instead, cross-referenced
by row). Every leaf is grouped by which strata-core/src/parse/grammar_*.rs file it touches, and
where one file collects more surface than a single leaf can carry at <=5 points, leaves are
chained by blocked_by against each other (same-file edits are not scope-disjoint from each
other even though they are scope-disjoint from every other file's leaf). Every leaf's title
line in the body starts with "OWNER-OWNED: strata surface change; owner reviews before
dispatch" per the coordinator correction in SYSDESIGN-INVENTORY.md: any leaf that needs a new
surface word touches strata-core/src/parse and the owner redesigns strata personally.

The `lattice` leaf (T-SYS-A-LATTICE) goes first: it is the single highest-leverage finding in
STRATA-EXPRESSIVENESS.md, and every leaf anywhere in this epic that needs "one more trust/label
rung" (tenancy isolation, compliance zones, environments, multi-region active-active/passive)
is blocked on it, directly or via the environment-axis note folded into the same ticket.
