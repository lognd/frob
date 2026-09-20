---
id: T-4662
title: 'Strata: end the measured friction (ratchet churn, zero-signal gates, boilerplate
  assumes) before any grammar change'
state: queued
kind: feature
origin: agent
created: '2026-09-19'
priority: critical
parent: null
tier: epic
sprint: v1.1.0
runs_last: false
milestone: 1.1.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: '2026-09-19: epic container; all file work lives in its
  story/leaf children, which carry the disjoint scopes'
triage_changes:
- field: milestone
  old_value: null
  new_value: 1.1.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-20'
- field: sprint
  old_value: v0.536.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
acceptance:
- text: Given the 23 measured findings in scratchpad/STRATA-FRICTION.md, when this
    epic closes, then every child under stories A/B/C has landed with a positive control
    (a named pytest node that fails at HEAD c8f56ef10 and passes after), and every
    DECISION child under story D carries an owner-recorded decision in its body.
  evidence: []
threat: null
component: strata
anchor: false
anchor_reason: null
land_commit: null
---
Source: scratchpad/STRATA-FRICTION.md, a measured audit at HEAD c8f56ef10 (dev),
2026-09-19. 23 findings SF-01..SF-23, 7 HIGH. Every number below is reproducible
from the command or path cited in that file; each was re-verified by the planner
with git grep / sed before filing.

WHY THIS EPIC EXISTS, AND WHY IT IS NOT A GRAMMAR EPIC
The owner is personally rethinking strata grammar and semantics. This epic
therefore deliberately excludes every finding whose fix is a grammar or
semantics change; those are filed as DECISION tickets under story (D), which
carry the evidence and the options and ask only for a recorded decision.
What is in scope here is the measured cost of operating the CURRENT language:
ratchet churn, zero-signal gates, uncached scans, and gate false positives.

THE HEADLINE NUMBERS
- 614,294 rule fires across 82 distinct rule ids in .frob/telemetry.jsonl.
  ZERO of them start with SYS. SELFAUDIT001 appears exactly once. (SF-01)
- 434 commits to design/frob.strata in 60 days (452 all-time) producing that
  one recorded finding. (SF-01)
- 138 commits to docs/design/registry/capability-via-ratchet.lock.json, ALL 138
  inside 60 days; 123 of them also touch design/frob.strata. (SF-02)
- capability_via_site_counts measured 23.03s cold, 17.83s warm in the SAME
  process -- no memoization at all. check --json median 717.1s, max 1684.5s
  (telemetry n=145). (SF-04)
- The ratchet lock carries 45 units of accumulated slack and 3 dead entries, so
  45 new capability sites can land today with SYS111 silent. (SF-05)
- 3 shadow capability keys live at the lock's JSON top level, outside `entries`,
  diverging from the real values, and the reader ignores them. (SF-03)
- All 33 assumes expire on the same day, 2026-10-15, and the "overdue assumes
  are gate failures" rule is not wired to any verdict. (SF-07)
- The elaborator WARNs on literally every design load: 570 occurrences across 45
  land logs, ~12.7 per land. (SF-11)

ORDER OF WORK
(A) ratchet lock and the SYS111 mechanism -- SF-02,03,04,05,13,14,20
(B) gate signal and false positives -- SF-01,11,15,16,17,18,19
(C) assumptions and claims as-implemented -- SF-07,23
(D) DECISIONS for the owner -- SF-08,09,10,12,21,22

The leaves under A/B/C are scope-disjoint by construction so three agents can
run in parallel; only the A chain carries real blockers.

RELATION TO THE KERNEL DECOUPLING EPIC
SF-06 (whole-file lease on design/frob.strata and the ratchet lock serializing
the whole fleet) is T-4598 and belongs to the KERNEL DECOUPLING epic. It is NOT
duplicated here; it is attached as a blocker on the one leaf whose job is to
rewrite the ratchet lock file itself.

ACCEPTANCE FOR THE EPIC
Every child under A/B/C is closed with a positive control -- a test that fails
at HEAD today and passes after -- and every child under D carries an owner
decision recorded in its body.
