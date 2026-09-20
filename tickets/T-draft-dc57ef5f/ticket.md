---
id: T-draft-dc57ef5f
title: 'DECISION: v1.0.0 definition of done -- the release criteria, the sprints that
  compose it, and what is explicitly post-1.0'
state: queued
kind: feature
origin: human
created: '2026-09-20'
priority: critical
parent: null
tier: epic
sprint: v0.533.0
runs_last: false
milestone: 1.0.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given the owner's confirmation, when frob ticket epic on this ticket runs,
    then every 1.0.0 criterion is a child epic or story with a done/total rollup
  evidence: []
- text: given the migration, when tickets with milestone 1.0.0 are listed, then every
    one has a parent inside the 1.0.0 set
  evidence: []
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-20: 72 tickets carry milestone 1.0.0 but they are scattered across ten sprints (v0.533 to v0.544 plus backlog), 70 of them are leaf tickets with no parent in the set, and only two epics are in it (T-3505 Windows works, T-3919 false-negative gates). Nothing in the ledger states what 1.0.0 means, so the milestone cannot be burned down. PROPOSED CRITERIA, owner to confirm or amend: (1) Throughput: a land completes in under 3 min median and the pre-land check is scoped (v0.533: T-4410, T-3611, T-5135, T-5139, T-4437). (2) Honest gates: every gate reports MEASURED / NOT_MEASURED / NOT_APPLICABLE (T-3203) and a missing tool is UNMEASURED and loud (T-5139); the false-negative epic T-3919 is closed. (3) Quality floors: WARN-tier gates burned to zero and promoted to ERROR (T-0969), coverage floors met (T-1273), NARR/DOCARCH narrative migration done (T-2994, T-3022). (4) Stable surface: CLI collapsed to about 15 ticket verbs with aliases (T-4687), no ticket citations in help or docs (T-5134), kernel boundaries enforced (T-4651). (5) Platforms: Windows works (T-3505), macOS CI green (T-2939, T-3213). (6) Sizing and accounting in place so 1.x planning is measurable (T-5132, T-5133, T-5137). (7) Dependencies current with live advisories (T-5138). EXPLICITLY POST-1.0 (move to milestone 1.1.0 or later): language expansion beyond C#/Unity (T-1597, T-3231), strata-as-language V-model (T-3004), strata expressiveness epics (T-3920, T-4662 beyond Story A/B), cross-repo portability (T-2964), the twelve consumer-audit epics in v0.538 except findings that block criterion 2, the web lint families (T-5140) which ship as 1.1 features. ACTION when confirmed: set milestone 1.0.0 on every ticket under the criteria epics and clear it from the 70 orphans (T-5133 migration does the mechanical part), then re-slice v0.535 to v0.542 into goal-named sprints in the criteria order.