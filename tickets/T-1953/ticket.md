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
scope:
- frob.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
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
