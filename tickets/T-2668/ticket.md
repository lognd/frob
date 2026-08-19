---
id: T-2668
title: 'land records ''gates: unmeasured'' and proceeds while a real SELFAUDIT001
  error sits in its own findings list'
state: in-progress
kind: bug
origin: human
created: '2026-08-19'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_reporting.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/tickets/_land_verify.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_verify.py
  reason: root cause of the unmeasured-gate-state bug lives in this file's gate-summary
    count regex (drifted since T-1664 added an unresolved term), not in _reporting.py
    alone
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/tickets/_land_verify.py
  reason: land-side reverify skips the identity-based (findings) comparison outright
    whenever gate_errors is None, even when error_findings IS measured -- the exact
    'discard a finding you already have' gap item 2 targets, on the land side
  actor: logan
  at: '2026-08-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Measured

T-2503 landed on 2026-08-18 and put a live SELFAUDIT001 ERROR onto main.
It is still there. Verified today by the coordinator, independently of the
agent who found it:

    uv run frob check --only sys --json | scripts/check_summary.py
    -> SEVERITY {'error': 13, 'warning': 3}
    -> SELFAUDIT001: self-audit family SYS107 node=testsuite:
       node 'testsuite' binds 601 file(s) (> 20) and declares a via-less ...

The mechanism, from T-2503's own Done report (`git show
a1c49a2a5:tickets/T-2503/done-report.md`, "Captured claims"), verbatim:

    gates: unmeasured (no parsable gate-summary from a fresh check)
    error-findings: AFFECT001@..., ..., SELFAUDIT001@design, ...

Two facts sit side by side in that record:

1. The gate-state claim is **unmeasured** -- the check that should have
   produced a parsable gate-summary did not.
2. The raw `error-findings` list **already contains `SELFAUDIT001@design`**.

So a real finding was present in the output, the summary parse failed, the
land treated the missing summary as "unmeasured" rather than as a failure
to verify, and it proceeded. The finding has been live on main ever since.

## This is recurring, not a one-off

The agent that found it hit the SAME shape on its own ticket minutes
earlier: `frob ticket done-report` warned "fresh frob check --ticket T-2634
produced no parsable gate-summary -- recording the Captured claims
gate-state as unmeasured".

So the done-report-time check invocation fails to produce a usable summary
routinely, and every land that hits it records `unmeasured` and continues.
Any finding present in that run is invisible to the gate-state claim.

## Why this is the dominant bug class in this repo, again

`unmeasured` is being treated as "no problem found". It is not -- it is
"could not determine whether there is a problem", and the two must not
share a code path. This repo has an explicit doctrine about exactly this
(epic T-2391, silent-zero): a zero that means "could not measure" must
never render or behave as "nothing to measure".

The prior art is close enough to check first: memory of a T-0627-related
failure where a land-time gate spawn was REFUSED under `FROB_AGENT` and the
empty result was read as unmeasured, then skipped permissively. Determine
whether this is the same root cause resurfacing or a distinct one -- if it
is the same, this ticket should extend that fix rather than add a parallel
one.

## Required fix shape

- A land whose gate-state cannot be measured must NOT proceed silently. It
  should refuse, or record a loud, distinct state that is visibly different
  from "measured clean" in both the Done report and LAND-PROOF.
- When the summary parse fails but raw findings ARE present, those findings
  must be used. Discarding a finding you already have because a formatter
  step failed is indefensible.
- Diagnose WHY the summary parse fails at done-report time. It happens
  often enough that two lands hit it within minutes today. That root cause
  is the real fix; refusing on unmeasured is the safety net.

## Do NOT

- Do NOT make the land refuse on any unmeasured state without first fixing
  the parse failure. If the parse fails routinely, a hard refusal blocks
  every land in the repo, and this fleet has already lost hours to gates
  that reddened main.
- Do NOT "fix" this by removing the gate-state claim from Done reports.
  LAND-PROOF's `claims_reverify` reads it.

## Positive controls, both directions

- a land whose check produces findings is BLOCKED (or loudly marked), and
  the findings appear in the Done report's gate-state claim, not only in
  the raw list
- a land whose check is genuinely clean still proceeds with a measured
  claim -- without this the fix is indistinguishable from blocking all lands
- a land whose check cannot run at all records a state that is visibly
  distinct from both of the above, and a human reading the Done report can
  tell which of the three happened
- reproduce the parse failure deliberately and confirm the new behavior;
  a fix validated only against a working check has not been tested
