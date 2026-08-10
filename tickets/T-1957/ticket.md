---
id: T-1957
title: Wire DUP001 region_kernel (R1.5) as regression corpus for type-name-only clone
  families (T-1938 finding)
state: done
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
- tests/fixtures/dup_type_name/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/fixtures/dup_type_name/**
  reason: 'Adding the regression fixture/test/corpus files this ticket''s own plan

    describes (tests/fixtures/dup_type_name/**, tests/unit/dup/**), plus a

    docs/modules/dup.md cross-reference noting this family as a live worked

    example of what region_kernel catches (the ticket''s own decision-2

    alternative to flipping the repo-wide default).

    '
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/dup/test_type_name_only_regression_t1957.py::TestTypeNameOnlyCloneMissedByDefault::test_default_config_does_not_catch_the_function_pair
- tests/unit/dup/test_type_name_only_regression_t1957.py::TestRegionKernelAloneCatchesTypeNameOnlyClone::test_region_kernel_flag_alone_finds_the_pair_at_similarity_one
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

## Done report

DID NOT flip `[dup].region_kernel` on repo-wide. Added the regression
corpus + test + docs cross-reference the ticket asked for, per its own
"NOT DONE BY T-1938" item 1, and MEASURED item 2's cost as a
recommendation rather than a silent side effect, exactly as directed.

CORPUS: tests/fixtures/dup_type_name/src/{mod_a,mod_b}.py reconstruct
the T-1938 shape standalone (check_backpressure_obligations/
check_fallback_obligations from src/frob/strata/_backpressure.py/
_fallback.py: two identically-shaped functions, each collecting
violations of its own domain-specific type -- BackpressureViolation/
FallbackViolation -- via two same-shaped helper calls, then logging a
count). Built and empirically verified by hand before writing the test
(not assumed): a too-trivial first draft of the fixture was ALREADY
caught by R2 alone, so it was NOT a faithful reproduction of the ticket's
claimed miss -- iterated until the fixture reproduced the real
measured behavior (docstrings + a bind_code/Result branch + an f-string
log call, matching the real functions' actual shape closely enough that
whole-body R1/R2 hashing genuinely misses it while R1.5 catches it).

TEST: tests/unit/dup/test_type_name_only_regression_t1957.py, 2 tests:
- test_default_config_does_not_catch_the_function_pair: with THIS
  repo's actual frob.toml shape (native_rungs_enabled=False,
  region_kernel_enabled left at its own False default), the
  check_backpressure_obligations/check_fallback_obligations pair never
  appears in any rung's output.
- test_region_kernel_flag_alone_finds_the_pair_at_similarity_one: with
  ONLY region_kernel_enabled=True changed (same native_rungs_enabled=
  False, no other flag touched), the pair appears at rung=r1.5
  similarity=1.0.
Both measured directly via a standalone script before committing to the
test shape (see Evidence below for exact node ids).

DOCS: docs/modules/dup.md gets a new "Worked example: catching a
'type-name-only' clone (T-1938/T-1957)" subsection under R1.5's own
section, citing the corpus and stating explicitly that whether to flip
the repo-wide default is a deliberately separate, open decision.

COST MEASUREMENT (the ticket's decision-2 ask, taken as a
recommendation, not applied): `frob check --only clones` on this repo,
region_kernel OFF (current default) vs ON (temporarily toggled in
frob.toml, then reverted -- confirmed `git diff frob.toml` empty
afterward):
  region_kernel=False (baseline): cold 4.67s, warm (FROB_NO_GATE_CACHE=1,
    fingerprint cache populated) 4.69s
  region_kernel=True:             cold 8.04s, warm 7.34s
Roughly +60-70% on the `clones` gate stage alone (~+3.3s wall), and
surfaces 2 new real DUP001 findings repo-wide (3 errors, 1 warning vs 1
error, 0 warnings at baseline -- expected, since the whole point of
turning it on is finding MORE real duplication; not triaged further,
out of this ticket's own scope). This is a single-machine, single-run
measurement, not a statistically rigorous benchmark -- treat as an
order-of-magnitude recommendation: RELATIVELY CHEAP on this repo's
current corpus size (a few seconds, not the multi-minute native_rungs
blowout T-0974 measured for R3-R5), but a real, non-zero repo-wide cost
every `frob check` would pay. RECOMMENDATION: given the cost is modest
and the corpus above already proves real value (a genuine production
miss caught), flipping `[dup].region_kernel = true` repo-wide looks
reasonable -- but this is the coordinator's call, not applied here.

LAND FOOTGUN HIT AND FIXED: `frob ticket land`'s pre-land `ty check`
passes this ticket's touched files as EXPLICIT paths, which overrides
`pyproject.toml`'s `[tool.ty.src] exclude = ["tests/fixtures/**"]` (ty's
own explicit-path-wins-over-exclude behavior -- confirmed: a bare `ty
check` with no explicit paths finds nothing under either
tests/fixtures/dup_type_name/ or the sibling tests/fixtures/dup_region/,
but explicit-path-checking either one directly resurfaces
unresolved-reference errors for their intentionally-undefined stand-in
names). Fixed by making both fixture files self-contained (a trivial
local `bind_code`/`log` stub instead of an intentionally-undefined
name) rather than touching pyproject.toml's exclude config -- re-verified
the dup-detection behavior (both tests) is unchanged after this edit.

Filed: none.

### Changed
```
 tickets/T-1957/done-report.md | 77 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-1957/ticket.md      | 22 ++++++++++++-
 2 files changed, 98 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/dup/test_type_name_only_regression_t1957.py::TestTypeNameOnlyCloneMissedByDefault::test_default_config_does_not_catch_the_function_pair` (pytest node id, verified passing when recorded)
- `tests/unit/dup/test_type_name_only_regression_t1957.py::TestRegionKernelAloneCatchesTypeNameOnlyClone::test_region_kernel_flag_alone_finds_the_pair_at_similarity_one` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 5 error(s), 978 warning(s), 712 waived
- error-findings: ARCH001@src/frob/tickets/_land.py, ARCH001@src/frob/tickets/_scope.py, COV001@src/frob/tickets/_scope.py, F401@/home/logan/projects/frob/.claude/worktrees/floor-final/tests/unit/test_tickets_evidence_only_scope.py, TEST001@src/frob/tickets/_scope.py
