---
id: T-1614
title: 'RUNS LAST: audit every frob:waive for cop-outs, after all other work is complete'
state: in-progress
kind: security
origin: human
created: '2026-08-05'
priority: high
blocked_by:
- T-1612
- T-1611
- T-1613
parent: T-1609
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: true
scope_breadth_ack_reason: 'standing periodic audit ticket per T-2467: scope is intentionally
  repo-wide since any file may contain a frob:waive directive to review'
no_scope_declared: true
no_scope_declared_reason: 'bounded scan-and-classify pass: read-only classification,
  cop-outs filed as separate scoped tickets rather than edited here'
scope_changes:
- op: remove
  glob: src/frob/**
  reason: 'bounded scan-and-classify pass per dispatch: no source edits planned this
    pass, cop-outs filed as separate tickets rather than fixed inline'
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: tests/**
  reason: 'bounded scan-and-classify pass per dispatch: no source edits planned this
    pass, cop-outs filed as separate tickets rather than fixed inline'
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: docs/**
  reason: 'bounded scan-and-classify pass per dispatch: no source edits planned this
    pass, cop-outs filed as separate tickets rather than fixed inline'
  actor: logan
  at: '2026-08-18'
body_changes:
- mode: append
  reason: 'T-2467: reshape from unreachable runs_last one-shot to periodic watermark-scoped
    audit'
  actor: logan
  at: '2026-08-18'
  old_length: 2480
  new_length: 4199
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Audit every frob:waive directive in the repository and confirm each is a genuine, still-necessary exception rather than a cop-out.

THIS TICKET RUNS LAST. Not last among the tickets that existed when it was filed -- last, absolutely. Tickets filed after this one also precede it. The blocked_by edges recorded here cover only what existed at filing time and are therefore a floor, never the whole precondition.

STANDING PRECONDITION, to re-check immediately before starting: every other ticket in the queue is done, dropped, or archived. If `frob ticket list --state queued` or `--state in-progress` returns ANYTHING other than this ticket, it is not yet time -- stop and work that instead. See the runs-last enforcement ticket for making this mechanical rather than a promise.

Why last: a waiver's honesty can only be judged against finished code. Many waivers name a follow_up ticket, and judging them before that work lands would condemn waivers doing exactly what they promised. A waiver audit run early produces confidently wrong answers -- it would delete honest waivers and bless ones whose justification has not yet expired.

For every waiver, decide one of:
- STILL NECESSARY AND HONEST -- the reason describes a real constraint that still holds. Keep. Confirm the reason explains WHY rather than restating the rule.
- OBSOLETE -- the condition passed, the code changed, or the follow-up landed. Remove the waiver and let the gate speak.
- A COP-OUT -- it exists because fixing the finding was inconvenient. Remove it and fix the underlying finding, or, if the fix is genuinely large, replace it with a real ticket and a waiver naming that ticket.
- PERMANENT BY DESIGN -- no follow-up will ever exist (a private test helper with no production caller is the canonical case). These need a way to say so; the permanent-waiver ticket already filed covers that gap.

Specific things this drive learned to look for:
- A reason that merely restates the rule name is not a justification.
- A follow_up pointing at a done ticket is an orphan, not a waiver.
- Waivers added in bulk during a burn-down deserve extra scrutiny: cop-outs cluster there.
- A waiver on a rule that structurally cannot fire (a diff-scoped rule judged on a full run) is noise, not an exception, and belongs in that rule's exemption list instead.

Deliverable: every waiver classified, obsolete and cop-out waivers removed, and a count reported by category. A waiver left unexamined defeats the exercise.

RESHAPED (T-2467, 2026-08-18): this ticket's `runs_last` precondition
("after all other work is complete") is unreachable by construction in a
repo with continuous ticket inflow -- it sat rot-flagged for 13+ days
with nobody legally able to start it despite all three of its blockers
(T-1611/T-1612/T-1613) being done. `runs_last` is now OFF.

This ticket's operating mode is now PERIODIC and WATERMARK-SCOPED instead
of one-shot-after-queue-empty: `frob ticket waive-audit scan` (T-2467,
`frob.app.ticket_runner._waive_audit`) reports which `frob:waive`
directives need classification since the last completed pass (tracked in
`.frob/waive-audit-watermark.json` via `frob.gates._waive_audit_watermark`),
bounded on a first run or a still-catching-up run rather than demanding
the whole corpus at once. `frob ticket waive-audit complete
--reviewed-count N --cop-outs N` records a finished pass and advances the
watermark -- refusing if the reviewed count does not match the scan, or
if a bounded catch-up pass still has uncovered waivers.

The classification rubric below (STILL NECESSARY AND HONEST / OBSOLETE /
COP-OUT / PERMANENT BY DESIGN) and the specific patterns this drive
learned to look for (reason-restates-rule, orphaned follow_up,
bulk-waiver clustering, structurally-unfireable-rule noise) are UNCHANGED
-- only the triggering/scoping mechanism changed. A reviewer runs `scan`,
classifies each `ScannedWaiver` per the rubric below, removes/replaces
obsolete or cop-out waivers, then runs `complete` with the count reviewed.

This ticket now represents the STANDING PROCESS, not a single terminal
audit -- it stays open/queued as the periodic mechanism's home rather
than closing once one pass finishes.
