---
id: T-4279
title: the gate cache's stat-trust margin is a fixed constant tuned to one mount,
  so a coarse-granularity filesystem still returns stale verdicts silently
state: queued
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a filesystem whose modification-time granularity is coarser than the
    trust margin, when two different contents are written outside that margin but
    within one granularity tick, then the cache does not return a stale verdict
  evidence: []
- text: given a filesystem whose granularity cannot be established, when the fast
    path is consulted, then it falls back to the content hash rather than trusting
    the stat pair
  evidence: []
- text: given the chosen margin, when it remains a constant anywhere, then the granularity
    range it is safe for is stated alongside it rather than implied
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE GATE CACHE'S NEW STAT-TRUST MARGIN IS A FIXED CONSTANT, BUT THE PROPERTY IT
DEPENDS ON VARIES BY FILESYSTEM. This is a follow-up to the stale-cache fix that
landed today, not a criticism of it: the fix is correct and well-sized on the
filesystem it was measured against. The concern is what happens on the ones it
was not.

WHAT THE LANDED FIX DOES. A modification-time-and-size match is no longer trusted
on its own when the recorded time is younger than a fixed margin; inside that
window the content hash is consulted instead. That closes the case where two
writes land inside one clock tick and produce an identical pair for different
content.

WHAT WAS MEASURED HERE, INDEPENDENTLY, AFTER THE FIX LANDED. On this repository's
own working mount, twenty back-to-back write-stat-rewrite-stat cycles produced an
identical time-and-size pair for genuinely different content NINETEEN times. The
same mount's modification-time granularity, measured separately, is finer than
five milliseconds. Those two numbers together are exactly why the fix works: the
collisions all occur within a single tick, far inside the margin, and any two
writes separated by more than the margin necessarily receive distinct times.

WHERE THAT REASONING STOPS HOLDING. The margin is sound only while the
filesystem's granularity is much finer than the margin. Filesystems exist whose
granularity is one or two SECONDS -- older removable formats, and some network
mounts, where the time is supplied by a server or truncated on write. On such a
mount two writes comfortably outside the margin can still share a modification
time, the fast path trusts the match, and the stale verdict returns. The failure
is silent and it is the same silent-pass shape the original fix was written to
eliminate.

THIS MATTERS BECAUSE THE TOOL IS NOT ONLY RUN HERE. The project is published for
downstream consumers whose checkouts live wherever their machines put them,
including network shares. A constant tuned against one developer's mount is a
portability assumption, and this project has already recorded that portability is
a property to be declared and checked rather than inherited from wherever the
code happened to be written.

WHAT A FIX SHOULD DO. Derive the margin from the filesystem's ACTUAL observed
granularity rather than hardcoding it -- measure once, cache the result per
filesystem, and set the margin to a safe multiple of what was measured. Where
granularity cannot be established, fall back to the content hash rather than to
the fast path, because the cost of an unnecessary hash is time and the cost of a
wrong trust is a gate that passes without looking.

DO NOT SIMPLY RAISE THE CONSTANT. A larger fixed margin trades throughput on
every fast filesystem for partial safety on slow ones and still guesses. If a
constant genuinely must remain, the report should state which granularities it is
safe for and what happens outside that range, so the assumption is written down
instead of implied.
