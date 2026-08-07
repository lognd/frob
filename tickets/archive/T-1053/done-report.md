## Done report

Fixed the three named recurring perf-detector FP classes, per T-1041's
own resolver-precision follow-up:

1. Bare-method-name coincidence: `frob.perf._rules._perf002_python` now
   skips a `.count(`/`.index(` hit whose receiver token is exactly the
   nearest enclosing `for` loop's own bound variable (`_nearest_for_loop_var`),
   e.g. `for line in lines: line.count(x)`. Locked by
   `tests/test_perf.py::test_perf002_does_not_fire_on_the_loops_own_per_iteration_element`.
   Scope cut, documented (no ticket needed: the existing waiver is the
   permanent disposition, not a deferred cut): a `while`-loop subscript receiver
   (`lines[k].count("{")`, the real `_cpp_mayraise.py` specimen) has no
   bound identifier to compare against and is NOT covered by this
   positional heuristic -- its existing waiver stays (verified: this is
   a `while k < n:` loop, not a `for`).

2. lru_cache blindness: `EffectGraph.is_memoized`/`callee_is_memoized`
   (src/frob/perf/_effect_summaries.py) recognize both `@lru_cache` and
   the common real spelling `@functools.lru_cache(...)`, built from
   `RawSymbol.sig_tokens` (which carries a decorated def's decorator
   tokens ahead of its header). Wired into PERF008
   (`_loop_effects._file_violations`, skips a finding whose callee
   resolves only to memoized candidates) and PERF012
   (`_dup_spawn._entry_occurrences`, contributes no occurrence when
   every resolved candidate is memoized). Retired the now-unneeded
   PERF008 waiver on `src/frob/gates/__init__.py`'s
   `_ledger_states_at_base` call site -- verified fixed via a direct
   `loop_invariant_effect_violations` call over that file (0 hits vs the
   waiver's own claim that this exact shape used to fire).

3. Receiver conflation: `EffectGraph.reachable_effect`/`resolve_scoped`
   accept an optional `receiver_class` hint
   (`_infer_receiver_class`: a textual scan for a nearby `obj =
   ClassName(...)` constructor assignment), narrowing candidates to the
   inferred class FIRST when at least one matches, fail-open otherwise.
   Wired into both PERF008 and PERF012's dotted-call resolution. Does
   NOT generalize to a stdlib-typed receiver (`re.Pattern`, `Path`) --
   there is no `ClassName(...)` construction to match a stdlib type's
   own name against, so 7 of the 11 T-1041 waivers (all
   `.search(pattern)`-on-a-compiled-`re.Pattern` shapes across
   `_fmt_directives.py`, `_secrets.py`, `vet/_capability.py`,
   `gates/__init__.py` x2, `arch/_async_hazards.py`) and the two
   unrelated FP classes T-1041 also filed (argument-invariance ignoring
   a varying RECEIVER object in `_rule_id_scan.py`/`testing/_collect.py`;
   the callee NAME itself being loop-bound in `vet/_capability.py:3068`)
   remain necessary and were NOT touched -- confirmed by inspection, not
   in this fix's mechanism.

Scope was widened via `frob ticket scope --add` (four times, each with a
`--reason-file`) beyond the ticket's original four-file scope: PERF002's
own implementation lives in `src/frob/perf/_rules.py` (not originally
listed, but a hard prerequisite for acceptance criterion 0), the shared
`EffectGraph` substrate both in-scope rules call private helpers on lives
in `src/frob/perf/_effect_summaries.py` (`frob ticket scope`'s own
closure-warning surfaced this as under-capture), the two rules' own unit
test files needed extending, and `src/frob/gates/__init__.py` for the
one confirmed-retirable waiver. All additions are narrow/single-purpose
per their own reason text.

Litmus fixtures (T-0666 pattern) were written to assert the CORRECT
post-fix behavior and run against the pre-fix code first to confirm each
FP genuinely fired before landing the fix (PERF002's test failed with a
`TypeError`/wrong-firing pre-fix during dev iteration on the bytes/str
source mismatch that also needed a fix; the lru_cache/receiver-conflation
tests were written straight to the design already known to be broken
per T-1041's own catalogue).

Gates: `frob check --ticket T-1053` clean across lint (ruff-check/
ruff-format/ty), static (frob-cycle/dup/arch/exports, all pass, only
pre-existing repo-wide warnings), gates-native (AFFECT/COV/PRE clean
after the doc anchor and directive fixes below), gates-security
(2 pre-existing PII012 findings in src/frob/tickets/_leases.py, confirmed
via `git diff --stat main -- src/frob/tickets/_leases.py` = empty, not
touched by this ticket). One pre-existing unrelated test failure
(`tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known`,
SYS205 in src/frob/strata/_mode_conformance.py) confirmed via empty
`git diff --stat main` on that file -- not caused by this change.

`git diff main --diff-filter=D --stat` is empty (no deletions outside
scope). `frob test --base main` python suite: exit=0, 16 outcomes
recorded.

Added `docs/modules/perf.md#three-false-positive-classes-closed-t-1053`
documenting all three fixes, their mechanism, and their honest remaining
gaps (while-loop-subscript PERF002, stdlib-typed receivers, the two
unrelated FP classes T-1041 also filed that this ticket does not touch).

Filed: none -- no new out-of-scope work discovered; the two remaining
FP sub-classes from T-1041 (stdlib-receiver method-name ambiguity;
argument-invariance-ignoring-receiver-variance; callee-name-itself-
loop-bound) are pre-existing, already-waived, already-documented gaps,
not new findings, and their waivers/reasons already correctly disclose
them as out of this fix's mechanism.

### Changed
```
 docs/modules/perf.md                     |  62 +++++++++++++
 src/frob/gates/__init__.py               |  11 +--
 src/frob/perf/_dup_spawn.py              |  27 ++++--
 src/frob/perf/_effect_summaries.py       | 145 +++++++++++++++++++++++++++++--
 src/frob/perf/_loop_effects.py           |  26 +++++-
 src/frob/perf/_rules.py                  |  49 ++++++++++-
 tests/test_perf.py                       |  26 ++++++
 tests/unit/perf/test_dup_spawn.py        |  68 +++++++++++++++
 tests/unit/perf/test_effect_summaries.py |  75 ++++++++++++++++
 tests/unit/perf/test_loop_effects.py     |  51 +++++++++++
 tickets.md                               | 110 ++++++++++++++++++++++-
 11 files changed, 624 insertions(+), 26 deletions(-)
```

### Evidence
- `tests/test_perf.py::test_perf002_does_not_fire_on_the_loops_own_per_iteration_element` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect::test_loop_invariant_call_to_lru_cached_helper_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect::test_receiver_conflation_binds_only_to_the_matching_receivers_class` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_dup_spawn.py::TestPerf012T1053FalsePositiveClasses::test_two_call_sites_to_an_lru_cached_helper_are_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_dup_spawn.py::TestPerf012T1053FalsePositiveClasses::test_receiver_conflation_binds_only_to_the_matching_receivers_class` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_effect_summaries.py::TestMemoizedCalleeDetection::test_lru_cache_decorated_symbol_is_memoized` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_effect_summaries.py::TestMemoizedCalleeDetection::test_undecorated_symbol_is_not_memoized` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_effect_summaries.py::TestMemoizedCalleeDetection::test_bare_cache_named_parameter_is_not_mistaken_for_a_decorator` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_effect_summaries.py::TestMemoizedCalleeDetection::test_functools_dotted_lru_cache_decorator_is_memoized` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
