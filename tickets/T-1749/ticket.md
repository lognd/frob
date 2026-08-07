---
id: T-1749
title: frob ticket evidence --designate-repro is a second silent BUG002-check-redirect
  asymmetry
state: queued
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_setters.py
- src/frob/gates/_mutation_evidence.py
- src/frob/app/ticket_runner/_verify.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Found while implementing T-1733's audit requirement ("every way to make a
ticket easier to close must cost at least as much bookkeeping as the
honest way -- report any others found"): `frob ticket evidence
--designate-repro NODE-ID` (`frob.tickets._setters.set_designated_repro_test`,
T-1670) is a second candidate for the same asymmetry T-1733 fixed for
`--replace`.

BUG002 (`frob.gates._mutation_evidence.bug_repro_violations`) checks
whichever evidence id is the ticket's "designated repro test" (explicit
`--designate-repro`, or the first bound id by default) for a genuine
FAIL-at-parent outcome. `--designate-repro` can retarget that check onto
a DIFFERENT already-bound id with:

- no `--reason`/`--reason-file` requirement
- no audit trail (no `EvidenceChangeEntry`-shaped record)
- no gate consuming the fact that a redesignation happened

`set_designated_repro_test` does require the target already be bound
(cannot invent a fresh unverified id), so this is narrower than the
`--replace` gap T-1733 fixed -- but it still lets an agent silently
redirect BUG002's check away from a test that genuinely still fails at
parent onto a weaker, already-passing-at-parent bound id, with zero
trace in the ledger. An agent facing a BUG002 refusal has this as a
quiet escape structurally parallel to unbinding via `--replace`.

Candidate fix, mirroring T-1733's own shape: require `--reason` on
`--designate-repro` (at minimum when RE-designating an already-set
value, since a first-time designation on a fresh ticket is closer to
"pure addition" and arguably should stay free, matching T-1733's own
"tax weakening, not strengthening" principle) and record it in a new
append-only audit field, surfaced by `frob ticket show` the same way
`evidence_changes` now is.

Not fixed here -- found during T-1733's audit pass, filed as the
"report any others" deliverable rather than silently expanding T-1733's
own scope.