---
id: T-1957
title: Wire DUP001 region_kernel (R1.5) as regression corpus for type-name-only clone
  families (T-1938 finding)
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/dup/**
- tests/unit/dup/**
- docs/modules/dup.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1938 deliverable 2 finding: DUP001 already HAS the capability to catch
type-name-only duplication -- it does not need a new detector, it needs
an existing opt-in rung turned on (or at least exercised as a regression
corpus).

EMPIRICAL PROOF (measured against the pre-dedup two-file pair
`_backpressure.py`/`_fallback.py`, before T-1938's own extraction landed):

- Default config (`region_kernel=False`, `native_rungs=False`, the
  repo's actual `frob.toml` shipped default): `find_clones` over the
  WHOLE repo found only 3 cross-file backpressure<->fallback pairs, none
  of them `check_backpressure_obligations`/`check_fallback_obligations`
  (the function containing the RELWAIVE002 block) -- this reproduces the
  ticket's original DUP001 miss.
- With ONLY `[dup].region_kernel=true` added (R1.5, still `native_rungs=
  false`, no native R3-R5 cost): 31 cross-file pairs, INCLUDING
  `check_backpressure_obligations <-> check_fallback_obligations` at
  `rung=r1.5 similarity=1.0`, plus every other RELWAIVE002-block-bearing
  function pair in the family
  (`_missing_bounded_intake_violations`/`_missing_fallback_violations`,
  etc).

WHY: `docs/modules/dup.md`'s own R1.5 section says the region kernel
runs over "the corpus's R2-NORMALIZED token stream" -- R2's alpha-rename
normalization, at REGION (sub-symbol) granularity via a generalized
suffix array. That is exactly "same shape, different identifier" --
which is exactly what a rename-only type name is. This rung was already
built (T-0193) for a different motivating case (copy-pasted sub-blocks)
and, as a side effect of reusing R2's normalization, already generalizes
over identifier renaming including a swapped violation-dataclass name.
It was invisible on this family only because `[dup].region_kernel` ships
off by default in this repo's `frob.toml` (perf: extra suffix-array
pass, T-0193's own opt-in default) -- not because the underlying
technique cannot see a type-name-only clone.

VERDICT: DUP001 CAN be generalized to catch type-name-only duplication.
No new detector logic is needed -- R1.5 already implements it. The
family T-1938 just deduplicated (RELWAIVE002 stale-waiver blocks,
21 sites, T-1938) is the natural regression corpus.

NOT DONE BY T-1938 (out of its `src/frob/strata/` scope, and
`src/frob/dup/`/`frob.toml` are flagged as another series' territory
this pass):
1. Add a `tests/unit/dup/` regression test that reconstructs a small
   two-function pair differing only in a violation-class name (the
   T-1938 shape) and asserts `find_clones(..., DupConfig(region_kernel_
   enabled=True))` reports an r1.5 pair -- so this exact miss class has
   permanent coverage.
2. Decide whether to flip `[dup].region_kernel = true` in this repo's
   own `frob.toml` (repo-wide perf tradeoff, T-0193's opt-in default,
   needs its own cold/warm cost re-measurement -- out of a strata-scoped
   ticket's remit) or leave it opt-in and rely on (1) alone plus a
   `docs/modules/dup.md` cross-reference noting this family as a live
   worked example of what region_kernel catches.

Filed as a residue ticket per T-1938's dispatch instructions rather than
touched directly, to avoid a scope/lease collision with the other agents
already working `src/frob/gates/` and (per T-1938's own dispatch note)
possible `src/frob/dup/` collisions this same wave.
