---
id: T-0597
title: 'frob-dup: triage duplicate-block report (75 groups, 112 waived) into extraction
  vs accepted-false-pair'
state: dropped
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
frob-dup currently reports 75 duplicate groups (112 waived), measured 2026-07-22 (was 64 groups at T-0204 filing, has grown). This is distinct from the frob-arch abstraction-opportunity advisories already covered by T-0393 -- frob-dup is the raw clone-detector report over both src/frob/** and tests/**, not the arch gate's near-dup-family suggestions. For each of the 75 groups: if it is a genuine extraction candidate (shared logic that should live in one home), extract it; if it is a false pair (coincidental structural similarity, e.g. parallel test scaffolding), waive it with an honest per-group reason. Acceptance: frob-dup summary line reports 0 unwaived groups (fixed or waived-with-reason), no threshold loosened without a disclosed decision.

## Failure log
- 2026-07-23 attempt 1: re-measured: frob-dup check stage now shows 240 groups/130 unaccounted (was 75 at filing, 3.2x growth in ~1 day of concurrent landings); too large for one honest per-group triage pass with real extraction+test verification -- split into T-0861 (25 src/frob/** extraction-candidate groups) and T-0862 (105 tests/**-only groups, mostly expected false pairs)

## Drop reason
- 2026-07-23: Superseded: re-measurement showed 3.2x pool drift (75 assumed -> 240 groups, 130 unaccounted) making the single-ticket scope undoable with honest per-group judgment; split into T-0861 (25 src extraction candidates) and T-0862 (105 tests-only scaffolding groups) per the attempt-1 fail log. (absorbed by T-0861)