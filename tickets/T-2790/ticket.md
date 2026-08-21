---
id: T-2790
title: 'frob check''s 274s cost is now the only lever on fleet throughput: profile
  the top four whole-program stages and decide what is reducible'
state: queued
kind: feature
origin: agent
created: '2026-08-21'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/investigations/
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
## Why this is the top lever

T-2782 measured and CLOSED the alternative. Landing is serialized on a
~300s critical section, and that section is dominated by one `frob check
--ticket` spawn. T-2782 proved the obvious workaround -- verifying outside
the lock -- cannot be made cheap: main moves between essentially every
consecutive land under real load (67 lands/24h; busiest-window inter-land
gaps 432/280/495/204/335s, the same order as one critical section), so an
optimistic scheme would be invalidated nearly every attempt and its
revalidation costs about as much as the original check.

That leaves the check's own cost as the only remaining lever on fleet
throughput. Read docs/investigations/T-2782-land-serialization.md FIRST --
it is the measurement this ticket stands on, and it also records what has
already been ruled out.

## Measured today (T-2782, cold `frob check --ticket`, 274.56s wall)

    sys              69.78s
    perf             59.63s
    archgate         45.44s
    dead_symbols     34.08s
    coverage         32.70s
    tickets          25.46s
    clones           18.15s
    refs             18.02s
    pii_structural   16.00s

Those nine are ~87% of stage time. The top four alone are ~209s.

For contrast, the fast per-file tools are already negligible: ruff 0.18s,
ty 4.90s, frob-dup 6.37s. There is no win available there.

Corroboration, not a single reading: this repo's own earlier
land-instrumented figure (T-1344/T-2053) put the check at ~209s of a
~95-320s land. Two independent measurements agree on the shape.

## What is already known and must not be re-derived

An earlier performance epic already moved these numbers -- archgate was
153s and sys was 145s at that time, so both have roughly halved already.
Find that work (search DONE/archived tickets for the frob check performance
epic and the Rust hot-path migration into frob_core) and read what it did
BEFORE proposing anything. The cheap wins are likely spent; assume the
remaining cost is structural until measured otherwise.

Note also that the whole-result replay cache (`[REPLAY age=...s, unchanged
tree]`) requires a byte-identical tree, so it never helps a land -- a
freshly-merged land tree is structurally never byte-identical. Any caching
proposal must state how it survives a merge.

## Required shape: measure, then decide -- do NOT start optimizing

First deliverable is a profile, not a patch. For each of the top four
stages (sys, perf, archgate, dead_symbols):

1. Where does the time actually go inside the stage? Profile it.
   `PYTHONFAULTHANDLER=1 timeout -s ABRT N` is effective here and has found
   a hotspot in this repo in ~180s before.
2. Is the work genuinely whole-program, or is it whole-program only by
   construction (e.g. it rebuilds a call graph or re-parses the tree that
   another stage already built)? Shared, computed-once analysis across
   stages is the most likely structural win -- several of these stages
   plausibly rebuild the same graph independently.
3. What is the incremental-correctness story? A stage that is genuinely
   whole-program cannot be diff-scoped without becoming unsound, and an
   unsound gate is far worse than a slow one. Say which stages are which.

Then propose, with the measurement attached. Split the actual optimization
work into child tickets (`--parent` this one) rather than doing it here.

## Constraints

- NEVER trade soundness for speed. A gate that gets faster by checking less
  is a silent-zero regression, which is this repo's dominant bug class
  (epic T-2391). Any narrowing needs a positive control proving the
  narrowed check still FIRES on a planted violation it must catch.
- Both-direction controls on any change: the finding set on this repo must
  be IDENTICAL before and after, on a real unbudgeted run. A speedup that
  changes the finding count is a behavior change, not an optimization --
  report it as such.
- Do not measure with `--budget`. A budget-truncated run drops whole stage
  groups and reports a fraction of the finding set; that mechanism already
  caused a class of false regressions here (T-2713/T-2715).
- No silent caps: if any proposal bounds work (sampling, top-N, skipping),
  log what was dropped.

## Acceptable outcomes

"The remaining cost is irreducible without unsoundness" is a legitimate and
valuable result if the measurements support it -- record it and close.
Do not manufacture an optimization.
