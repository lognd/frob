---
id: T-4338
title: CI does not pin the uv version, so platform legs silently run different toolchains
state: queued
kind: bug
origin: human
created: '2026-09-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
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
THE INTEGRATION RUN DOES NOT PIN THE VERSION OF THE TOOL IT BUILDS AND TESTS WITH,
SO THE THREE PLATFORM LEGS CAN SILENTLY RUN DIFFERENT TOOLCHAINS, AND ONE ALREADY
DID.

MEASURED, AND IT COST TWO TICKETS TO FIND. A cascade of 68 failing tests appeared
on one platform leg and not another, for the same commit. Two rounds of
investigation went into it. The eventual measured cause was not an operating
system difference at all: the setup action caches the tool binary under a key
including OS, architecture and system Python version. One leg hit its cache and
reused an older tool; the other missed, downloaded the current release, and that
release had added a stricter validation rule that the older one did not enforce.
The platform that "worked" was not correct -- it was stale.

WHY THIS IS DANGEROUS RATHER THAN MERELY UNTIDY. The immunity of the passing legs
is an accident of cache state, and cache keys miss routinely -- on a runner image
bump, an architecture change, a Python version change, or eviction. So the same
failure is waiting for every other leg, and it will arrive detached from any
commit that could explain it. Worse, the failure presents as a platform-specific
bug, which is what sent the first investigation down the wrong path: a whole
ticket concluded a plausible mechanism that was not the real one, because the
platform difference looked like the obvious explanation.

A BUILD THAT CANNOT SAY WHICH TOOLCHAIN IT USED CANNOT BE REPRODUCED. That is the
deeper problem. A red run is only actionable if the same inputs can be replayed;
an unpinned, cache-dependent tool version means two runs of the same commit are
not necessarily the same experiment.

PIN THE TOOL VERSION EXPLICITLY ACROSS EVERY LEG, in the one place that governs
all of them, so the legs are comparable by construction. Check whether other
tools the workflow installs have the same exposure rather than fixing only the one
that bit us -- the interesting question is how many unpinned toolchain inputs this
workflow has, not just this one.

MAKE THE RUN STATE WHAT IT USED. Whatever is pinned, the run should print the
resolved versions somewhere a reader of a failed run will see them. A version that
must be inferred from cache-hit logs is not reported.

DECIDE HOW PINS GET UPDATED before you add them, and record it. A pin that nobody
ever advances becomes its own liability -- the project already has dependency
automation, so say whether these pins are in its scope or deliberately outside it.

VERIFY by confirming the resolved tool version is identical across all three
platform legs of one run, and quote the three values. Identical pins in the
configuration file are not the evidence; the versions the legs actually resolved
are.
