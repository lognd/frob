---
id: T-2393
title: BUG002 has no front door for tickets with no behavioral delta
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: Given a doc-only, epic-rollup, or purely structural ticket, when it is closed
    with an explicit mandatory reason, then BUG002 accepts it via a first-class CLI
    flag without any ledger hand-edit, and the reason is recorded.
  evidence: []
- text: Given a ticket with genuinely confirmatory-only evidence and no such flag,
    when it is closed, then BUG002 still refuses, proving the gate was not weakened.
  evidence: []
threat: null
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED TODAY: three separate tickets were blocked at close/land time
by BUG002 (`EvidenceConfirmatoryOnly`) despite having no runtime defect
to reproduce -- T-1662 (epic closure, kind=security), T-2341 (kind=bug
but every change structural/doc), and T-2346 (needed
`--designate-repro-force` for a related reason).

The gate is CORRECT in general: evidence must fail at the parent commit,
not merely confirm current behaviour. But a ticket whose deliverable is
documentation, an epic rollup, or a pure structural refactor has no
behavioural delta to demonstrate, and the gate has no way to know that.

A remedy already exists -- `frob:no-behavior-change reason="..."` in the
ticket body -- but it is reachable ONLY by hand-editing the ledger
(see T-2392), so the safe path and the available path diverge.

FIX: surface the existing remedy as a first-class flag, e.g.
`frob ticket close --no-behavior-change --reason TEXT`, writing the same
directive through the validated mutation path. Keep the reason
MANDATORY -- this must stay prove-or-justify, not an escape hatch. Do
NOT weaken BUG002 itself; the gate has caught real confirmatory-only
evidence and `--check-repro` runs in ~1.5s. The defect is the missing
front door, not the lock.
