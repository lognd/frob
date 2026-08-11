---
id: T-2129
title: LAND-PROOF reports verified=SKIPPED-UNMEASURED/ERROR for a successful QUEUED-with-failure-log
  land (is_ancestor_of_main=True contradicts its own ERROR)
state: queued
kind: bug
origin: agent
created: '2026-08-11'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/**
- src/frob/app/ticket_runner/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: Given a QUEUED ticket with a recorded failure log landed via frob ticket land
    (publishing the failure log to main, no done transition), when the LAND-PROOF
    self-check runs, then it reports verified=True (or an equivalently non-error terminal
    outcome) instead of an ERROR that contradicts its own printed is_ancestor_of_main=True
    field
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
`frob ticket land T-2109` (a QUEUED ticket with a recorded failure log,
never DONE -- `frob ticket fail` requeues rather than closing) actually
published its content to main correctly: commit
`0106ba15d9b3e64d19a866dcff2f6a3b9802230d`, confirmed both required
ways --

  git merge-base --is-ancestor 0106ba15d9b3e64d19a866dcff2f6a3b9802230d main
  # exits 0, real ancestor

  git show --stat 0106ba15d9b3e64d19a866dcff2f6a3b9802230d
  # 3 files, includes tickets/T-2109/ticket.md with the Failure log section

  python3 scripts/verify_lands.py 0106ba15d9b3e64d19a866dcff2f6a3b9802230d
  # ON HEAD

But `frob ticket land`'s own end-of-run self-check printed:

  LAND-PROOF: ticket=T-2109 commit=0106ba15d9b3e64d19a866dcff2f6a3b9802230d
  is_ancestor_of_main=True state_on_main=queued
  claims_reverify=skipped-unmeasured verified=SKIPPED-UNMEASURED
  ERROR: ticket land: T-2109 LAND-PROOF did not verify -- the commit
  ... did NOT reach `main` (or the ticket's on-main state is not
  terminal); treat this land as FAILED despite the 'landed as' line
  above ...

`is_ancestor_of_main=True` on the SAME line the ERROR message claims
"did NOT reach main" -- the self-check's own printed fields already
contradict its own conclusion. The real defect: for the QUEUED-with-
failure-log shape (T-2109's own new code path, printed one line
earlier: "T-2109 is QUEUED with a recorded failure log, not landing a
done ticket -- publishing the failure log to main as-is, no done
transition attempted"), the LAND-PROOF verifier's terminal-state
allowlist evidently does not include `queued` as an acceptable
post-fail state, so a genuinely successful publish is reported as a
failed one. An operator trusting the ERROR line alone (rather than
manually re-deriving ancestor-of-main and diffing content, exactly as
this ticket's own error message tells them to) would wrongly believe
the fail record never reached main and could re-attempt or
hand-recover a commit that was already there.

Likely fix location: whatever function computes `verified=` from
`is_ancestor_of_main`/`state_on_main` needs to treat `queued`
(specifically: queued WITH a non-empty failure log, the exact shape
`frob ticket fail` produces) as an acceptable terminal state for this
one land shape, alongside whatever states already pass (`done`,
presumably `dropped`/`blocked`). Scope not identified precisely --
whichever module owns the post-land verification message quoted above
(printed by the `frob ticket land` CLI path, likely in
`src/frob/app/ticket_runner/` or `src/frob/tickets/_land*.py`).
