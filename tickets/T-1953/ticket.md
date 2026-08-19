---
id: T-1953
title: 'TEST005 ratchet step 1: bump floors to 80/75 once a fresh measurement clears
  them'
state: queued
kind: feature
origin: human
created: '2026-08-10'
priority: low
parent: T-1273
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- frob.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: priority
  old_value: low
  new_value: low
  reason: owner decided to hold the ratchet; not actionable until a fresh measurement
    on a green suite
  actor: logan
  at: '2026-08-19'
body_changes:
- mode: append
  reason: 'owner decision: hold floors at 75/70, do not ratchet; held not dropped'
  actor: logan
  at: '2026-08-19'
  old_length: 2149
  new_length: 3813
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-1315 (TEST005 floor ratchet-up schedule) designed a concrete, staged
ratchet from the current recalibrated floor (unit_branch_cov=75,
module_line_cov=70, frob.toml [testing]) toward the pre-recalibration
aspirational target (90/85), per docs/design/test005-ratchet-schedule.md.

This ticket is STEP 1 of that schedule: unit_branch_cov 75 -> 80,
module_line_cov 70 -> 75.

TRIGGER (must hold before this ticket can close):
1. A coordinator runs a full, fresh `make coverage` (this is explicitly
   a coordinator-only step per docs/guides/agent-playbook.md section 6b
   -- a dispatched sub-agent must not attempt it) followed by
   `frob check --stamp-coverage` to produce a current
   frob-coverage.lock.json.
2. `frob check --only test` at the CURRENT floor (75/70) reports 0
   TEST005 findings against that fresh measurement.
3. The freshly stamped frob-coverage.lock.json's `module_line` map shows
   ZERO modules below 75% line coverage (the step-1 target for
   module_line_cov) -- i.e. bumping the floor to 75 creates no new
   red. Query: every `module_line` value < 75.

ACTION once the trigger holds:
- Bump frob.toml [testing] unit_branch_cov to 80 and module_line_cov to
  75.
- Extend (not replace) the existing T-0969/T-1315 rationale comment
  block with this step's own date and the measurement that justified it.
- File the STEP 2 follow-up ticket (unit_branch_cov 80->85,
  module_line_cov 75->80), same trigger shape, before closing this one --
  the schedule is only live if each step re-files its own successor.

If the trigger does NOT hold (some modules still sit below 75%), this
ticket should be left queued/blocked rather than forced -- do not lower
the bar to make the numbers fit. Re-measure later.

RECOVERY NOTE (T-1934): this ticket originally existed as draft
T-draft-fd2c5ba4 on the abandoned branch runner-wiring, filed by T-1315's
own done-report but never landed (the agent that filed it died before
`frob ticket land`). Recreated verbatim from that branch's content during
T-1934's investigation into unlanded branch work; the original draft on
runner-wiring was never landed and is superseded by this ticket.



## OWNER DECISION (2026-08-19): do NOT ratchet -- hold floors where they are

The repo owner has decided: **keep the coverage floors at their current
values (75/70). Do not bump to 80/75.**

This ticket is therefore NOT ready to work, and should not be picked up as
if the bump were still the plan.

Rationale recorded so this is not silently reversed later: at the time of
the decision, 18 tests were red on unmodified main (now tracked as
T-2630..T-2637, several already fixed) and the ticket queue was running at
break-even. Raising a coverage floor in that state adds failures to a suite
people are already learning to discount, which is how a red signal stops
being read at all. The ticket's own premise required "a fresh measurement"
that was never taken.

### What would change this

A fresh, unscoped TEST005 measurement stated against its denominator, taken
when `tests/unit/` is green on unmodified main. If that measurement shows
the packages are already comfortably above 80/75, the bump is cheap and the
owner may revisit. If it shows a large gap, the bump is a burndown campaign
and needs to be sized as one -- see T-1273 (per-package campaign to the
CURRENT 75/70 floors) and T-1661 (55 remaining findings), both of which
target the existing floors and remain valid work.

### Explicitly NOT dropped

This ticket is being HELD, not cancelled. Dropping is terminal in this repo
and the owner may want the ratchet later once the suite is green. Leave it
queued at low priority with this decision recorded.

Do not treat the existing 75/70 floors as provisional in the meantime --
they are the current contract and T-1273/T-1661 exist to reach them.