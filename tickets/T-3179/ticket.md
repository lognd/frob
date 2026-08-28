---
id: T-3179
title: Attribution engine records UNATTRIBUTED for findings with a directly findable
  cause (2 measured)
state: queued
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/verify/_attribution.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/verify/_attribution.py
  reason: attribution engine; the two measured misses are decided here
  actor: logan
  at: '2026-08-27'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-27, TWO INDEPENDENT MISSES IN ONE DRIVE, same mechanism. The
sweep recorded each finding with `commit=None, ticket=None` (UNATTRIBUTED) even
though a specific commit was the direct and findable cause:

  1. T-3160's `missing-argument`: T-3152 changed `_process_start_age_s`'s
     signature; a stale 3-arg call site broke as a direct consequence. This was
     a genuine runtime `TypeError`, not merely a type-checker complaint.
  2. T-3172's `SYS003`: attributable to T-3151 at `5ced56304`.

Two misses on the same mechanism in one drive is systematic, not incidental.

WHY THIS COSTS MORE THAN IT LOOKS. An UNATTRIBUTED finding is the exact shape
that pins quarantine hardest, because attribution failure is what makes a
finding undisposable by the normal path. A finding that COULD have been
attributed but was not therefore converts a routine auto-filed ticket into a
fleet-wide landing stall requiring manual coordinator disposal.

WHAT TO DETERMINE FIRST (do not assume a cause):
  - Whether the attribution engine EXAMINED these commits and rejected them, or
    never considered them. Those are different bugs with different fixes and the
    distinction must be measured, not inferred.
  - Whether T-2929's correct refusal-to-attribute-against-a-stale-baseline is
    firing here. If so this is not an attribution bug at all but a baseline
    freshness problem, and the fix belongs there instead. Say which it is.

DO NOT WEAKEN THE GUARD. T-2929 (refuse to attribute against a stale baseline)
is correct and must stand. A fix that attributes MORE by lowering the evidence
bar would produce confidently-wrong attributions, which are worse than
UNATTRIBUTED -- a wrong commit sends the next agent to the wrong place. A stale
baseline already reported 5 of 6 "new" identities as new when they were
pre-existing.

ACCEPTANCE
- For each of the two measured cases, a stated determination: examined-and-
  rejected, or never-considered, with the evidence for that determination.
- If a defect is found, a must-fire fixture per case AND a must-stay-quiet
  fixture proving a genuinely unattributable finding still records UNATTRIBUTED
  rather than being force-matched to a nearby commit.
- No relaxation of T-2929. State explicitly that it still refuses on a stale
  baseline, with a test.
