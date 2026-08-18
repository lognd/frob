---
id: T-2406
title: 'deferred verification drains self-refuse and discard: 49% of post-land sweeps
  never run'
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: Given a post-land drain spawned by its own land, when it starts, then it excludes
    that originating land from its process scan and runs, rather than self-refusing.
  evidence: []
- text: Given a drain refused because a genuinely different land is running, when
    it declines, then the request is queued or retried rather than discarded, and
    the pending entry is observable via frob verify status.
  evidence: []
- text: Given a completed land, when its deferred sweep finishes, then the verify
    watermark commit_sha has advanced, asserted on the watermark value and not on
    exit status.
  evidence: []
- text: Given a drain that is genuinely blocked, when frob verify status runs, then
    it reports the count of drains refused since the watermark, so the condition cannot
    be silently invisible.
  evidence: []
threat: null
component: verify
anchor: false
anchor_reason: null
land_commit: null
---
THE ENTIRE DEFERRED-VERIFICATION ARCHITECTURE IS ~49% INERT. Measured
directly from `.frob/verify-drain/*.log`, 47 drain attempts this drive:

    23 of 47 (49%) refused and DISCARDED the work
    24 of 47        actually ran

The refusal text is identical in all 23:

    WARNING: tickets: refused -- a `frob ticket land` process (pid N) is
    running against this repository for T-XXXX ... retry after it completes
    verify drain: a land is in progress -- declining to start
    (NOT QUEUING, NOT RETRYING)

TWO DISTINCT DEFECTS, both required for the outage:

**(1) SELF-REFUSAL -- 13 of the 23.** The refusal names the SAME ticket
as the drain itself:

    log=T-1777 refusal names T-1777      log=T-2380 refusal names T-2380
    log=T-1860 refusal names T-1860      log=T-2386 refusal names T-2386
    log=T-2165 refusal names T-2165      log=T-2392 refusal names T-2392
    log=T-2299 refusal names T-2299      log=T-2393 refusal names T-2393
    log=T-2321/2322/2325/2330/2333 likewise

The post-land drain is spawned BY the land, WHILE that land is still
running, so the guard sees its own parent and declines. A land's own
deferred sweep is not a competing land. This is precisely the T-1914
self-sibling bug class that T-2289 already fixed once for sibling-state
regression ("a ticket is not its own sibling"); the same mistake is
present here in the drain's process scan.

**(2) DROP INSTEAD OF QUEUE -- all 23.** Even the 10 refusals caused by a
GENUINELY different concurrent land are wrong in their disposition. The
guard is right to decline to RUN concurrently; it is wrong to discard
the request. "not queuing, not retrying" makes deferred verification
lossy by design, so debt accumulates monotonically and never recovers,
no matter how quiet the fleet later becomes.

MEASURED CONSEQUENCE, right now, on a clean root with ZERO lands in
flight:

    watermark:               0adf7e911 (verified_at 04:14:21Z)
    watermark age:           4732s   (warn threshold 3600s)
    commits since watermark: 70      (warn threshold 5)
    unverified depth:        6 queued land-intents
    quarantine:              clear

The watermark has not advanced in ~79 minutes across 70 commits. This is
NOT the self-correcting backlog behaviour previously observed and
recorded (T-2324 took 570 -> 6); it does not drain during quiet periods
because the requests were destroyed, not deferred.

WHY THIS IS CRITICAL RATHER THAN MERELY WRONG. Every land reports
success and records "deferred post-land sweep", and roughly half of
those deferrals silently evaporate. The operator-visible signal says
verification was scheduled; no signal ever says it was dropped. That is
the [[silent-zero-is-the-dominant-bug-class]] pattern applied to the
verification pipeline itself -- the component whose entire job is to
notice problems is the one silently not running. It also primes the
quarantine death spiral: a large unverified backlog that finally does
get swept is far more likely to surface findings in bulk, raise
quarantine, and switch deferred landing off fleet-wide.

FIX SHAPE.
  - The drain must exclude its OWN originating land from the
    process/lock scan. Scope the exclusion to that specific pid/ticket,
    not to "any land", or the guard is deleted rather than corrected --
    an exemption matching the normal case disables the guard.
  - A refusal caused by a genuinely different land must QUEUE (or
    retry with backoff), never discard. The queue already exists
    (`.frob/verify-queue.json`, updated correctly by lands) -- the drain
    path simply is not using it on the refusal branch.
  - A dropped or deferred drain must be VISIBLE. `frob verify status`
    should report drains refused-and-dropped since the watermark, so
    this condition can never again be invisible for 79 minutes on a
    clean tree.

POSITIVE CONTROLS, both directions, mandatory:
  - must-still-refuse: a drain started while a genuinely DIFFERENT land
    runs must not execute concurrently (the guard's real purpose
    survives) -- but must now be queued rather than dropped, and the
    queue entry must be observable.
  - must-now-run: a post-land drain spawned by its own land must
    execute rather than self-refuse.
  - must-advance: after a land completes, the watermark must advance;
    assert on the watermark commit_sha changing, not on exit status.
    A drain that exits 0 having done nothing is the current behaviour
    and would pass any exit-code-based test.
