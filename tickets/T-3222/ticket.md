---
id: T-3222
title: 'Post-land sweep files findings that are 90% stale: 27 of 30 identities across
  two samples no longer reproduce'
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-27/28, TWO INDEPENDENT SAMPLES, same conclusion: the post-land
sweep files tickets whose findings are overwhelmingly already gone by the time
anyone reads them.

  Series CP (sweep residue batch: T-3158, T-3154, T-3160, T-3112)
      25 identities total -> 3 live, 22 stale residue

  Series DC (unattributed sweep regressions: T-3013, T-3017, T-3027)
      5 identities total  -> 0 live, 5 stale residue

  COMBINED: 30 identities, 3 live, 27 stale. A 90% false-positive rate.

Both samples were re-measured directly against current main (gates-fast, ruff,
and manual scans as appropriate), not inferred. Each stale ticket was closed with
the specific negative evidence recorded.

WHAT THIS COSTS. Every one of these tickets consumed an agent's full triage
cycle: read the body, reproduce, measure, close, land. Three separate series were
spent this way. That is the dominant consumer of drain capacity on this queue,
and it is spent almost entirely on findings that no longer exist. It also
poisons the queue's signal -- an operator reading 130 queued tickets cannot tell
which are real, so the genuinely live ones wait behind noise.

DO NOT FIX THIS BY FILING FEWER FINDINGS IN GENERAL. The sweep exists because
unaccounted-for regressions are a build failure here, and 3 of the 30 WERE real
(including T-3160's stale 3-arg call to `_process_start_age_s` after T-3152
changed its signature, which raised a genuine runtime TypeError). Suppressing the
sweep would have missed those. The defect is the ratio, not the existence.

LIKELY MECHANISMS TO INVESTIGATE (measure, do not assume -- and note that several
tickets this drive asserted a cause that was never verified):
  - The rolling baseline is behind the tree the sweep measures, so findings that
    a concurrent land already fixed are recorded as new. There is a known prior
    instance: a stale baseline reported 5 of 6 "new" identities as pre-existing.
  - The sweep is detached and deferred (T-1684), so by the time it runs, sibling
    lands have moved main. A finding true at spawn time may be false at file
    time. If so, the fix may be to RE-VERIFY each identity at file time rather
    than trusting the measurement taken at spawn.
  - No liveness check at all before filing.

WHAT IS WANTED:
  1. Determine which mechanism actually produces the 27. State the evidence.
  2. Re-verify each identity immediately before filing, and file only what still
     reproduces. If re-verification is too expensive to do synchronously, say so
     with a measurement and propose the alternative.
  3. For identities that do not survive re-verification, record them somewhere
     cheap (debt, a log line) rather than as a ticket that costs an agent a full
     triage cycle. Do not silently drop them -- a finding that appeared and
     vanished may still be real intermittently.

ALSO IN SCOPE, the related known defect: two byte-identical ticket pairs were
found tonight (T-3158/T-3159, and T-3022/T-3023 -- same title AND same body).
Series CP could not identify the duplicate-filing code path and correctly declined
to guess. If the mechanism is in the sweep's filing path, it belongs here; if it
is elsewhere, file it separately rather than folding it in.

ACCEPTANCE
- The mechanism behind the 90% stale rate identified, with evidence.
- Identities re-verified at FILE time; a must-fire fixture (a still-live finding
  is filed) and a must-stay-quiet fixture (a finding fixed between spawn and file
  time is NOT filed as a ticket).
- A measured before/after ratio on a real sweep batch, using the same counting
  method as above.
- The 3-of-30 genuinely live findings must still be caught. Prove it -- a fix
  that achieves a low false-positive rate by filing nothing is a regression.
