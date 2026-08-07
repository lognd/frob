## Done report

## Done report

Changed:
- src/frob/perf/_effect_summaries.py (new) -- EffectGraph, Unknown, UNKNOWN_KIND, EffectArg, EffectOccurrence
- src/frob/perf/_effect_summaries.py::EffectGraph
- src/frob/perf/_effect_summaries.py::EffectGraph.__init__
- src/frob/perf/_effect_summaries.py::EffectGraph.reachable_effect
- src/frob/perf/_effect_summaries.py::EffectGraph._reachable
- src/frob/perf/_effect_summaries.py::EffectGraph.resolve_scoped
- src/frob/perf/_effect_summaries.py::EffectGraph._direct_occurrences
- src/frob/perf/_effect_summaries.py::EffectGraph.summary
- src/frob/perf/_effect_summaries.py::EffectGraph._summary
- src/frob/perf/_effect_summaries.py::Unknown (class + __init__ + __repr__)
- src/frob/perf/_effect_summaries.py::_index_file_occurrences (now carries callee_name, 4-tuple)
- src/frob/perf/_loop_effects.py::loop_invariant_effect_violations (migrated onto EffectGraph)
- src/frob/perf/_loop_effects.py::_file_violations
- src/frob/perf/_dup_spawn.py::duplicate_spawn_violations (migrated onto EffectGraph)
- src/frob/perf/_dup_spawn.py::_entry_occurrences (Unknown emission)
- src/frob/perf/_dup_spawn.py::_def_violations (skips UNKNOWN_KIND when grouping)
- src/frob/perf/_rules.py (import path update: EffectGraph from _effect_summaries)
- docs/modules/perf.md (new substrate section + PERF008/PERF012 sections rewritten; structural-twin note on .strata REL310/311)
- tests/unit/perf/test_effect_summaries.py (new)
- tests/unit/perf/test_loop_effects.py (+2 tests: 3-hop, unresolvable-callee)
- tests/unit/perf/test_dup_spawn.py (+2 tests: 3-hop sibling-split, unresolvable-dynamic-dispatch)

Design: promoted PERF008's `_EffectGraph` (T-0775/T-0919, previously
private to `_loop_effects.py`) into its own module,
`frob.perf._effect_summaries`, as `EffectGraph` -- a documented public
surface (`reachable_effect`, `summary`, `resolve_scoped`) both PERF008 and
PERF012 now import rather than either owning the graph. Added `Unknown`
(identity-only equality) and `UNKNOWN_KIND` so an unresolvable binding
(ambiguous/external callee, unrecoverable argument text, budget-exhausted
walk) surfaces as an explicit occurrence member instead of silently
contributing nothing -- `Unknown` can only ever widen visibility, never
manufacture a false duplicate, because it never compares equal to
anything but itself. Fixed a real false-positive this surfaced during
development: `_called_names_from_tokens` extracts a call's bare/attribute
name for graph edges regardless of whether the call is itself a KNOWN
effect (e.g. the `run` in `subprocess.run(...)`) or a genuine local
callee -- without correlating that name against the symbol's own direct
occurrences, every ordinary resolved effect call would ALSO look like an
unresolvable second callee. Fixed by carrying the callee name alongside
each direct occurrence and skipping Unknown-emission for names already
accounted for that way (implemented, not band-aided with a blanket name
exclusion list, which was tried first and rejected as overly broad).

Per-criterion evidence (bound via `frob ticket evidence --accepts`):
- (a) 2+ hop callees fire identically: tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect::test_loop_invariant_spawn_call_three_hops_deep_is_flagged, tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_three_hop_duplicate_split_across_sibling_callees_is_flagged (both build on the pre-existing 2-hop precedents, which still pass)
- (b) argv-equivalence across sibling callees: tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::{test_two_helpers_spawning_identical_subprocess_is_flagged, test_multi_hop_duplicate_via_different_intermediate_callees_is_flagged, test_three_hop_duplicate_split_across_sibling_callees_is_flagged} (the last uses differently-whitespaced but argv-equivalent argument text)
- (c) explicit Unknown + per-rule Unknown policy: tests/unit/perf/test_effect_summaries.py::{TestEffectGraphSummaryUnknownDegradation::test_ambiguous_cross_file_callee_yields_an_explicit_unknown_member, TestUnknownIdentityEquality::test_two_unknowns_with_the_same_reason_text_are_not_equal}, tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_unresolvable_dynamic_dispatch_callee_never_manufactures_a_duplicate, tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect::test_unresolvable_callee_does_not_crash_and_does_not_fire. Unknown policy documented in each rule module's own docstring (_loop_effects.py, _dup_spawn.py) and in docs/modules/perf.md.

Filed: none (structural twin to .strata REL310/REL311 noted in
docs/modules/perf.md rather than wired -- different domain, declarative
node/attr graph vs. python AST call graph, and src/frob/strata/** is out
of this ticket's scope; no separate ticket needed since it is documented
as a deliberate non-wiring, not deferred work).

Gates: `uv run frob check --ticket T-0922` clean (0 errors, 3964
warnings, 219 waived -- matches the pre-existing repo-wide baseline,
nothing new introduced). `uv run frob test --base main` (touched-set,
19 python outcomes) exit=0. `uv run pytest -q tests/unit/perf/` all
pass (unrelated perf tests unaffected by the migration).

### Changed
(no changed files detected)

### Evidence
- `tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect::test_loop_invariant_spawn_call_three_hops_deep_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_three_hop_duplicate_split_across_sibling_callees_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_two_helpers_spawning_identical_subprocess_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_multi_hop_duplicate_via_different_intermediate_callees_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_effect_summaries.py::TestEffectGraphSummaryUnknownDegradation::test_ambiguous_cross_file_callee_yields_an_explicit_unknown_member` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_effect_summaries.py::TestUnknownIdentityEquality::test_two_unknowns_with_the_same_reason_text_are_not_equal` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_unresolvable_dynamic_dispatch_callee_never_manufactures_a_duplicate` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect::test_unresolvable_callee_does_not_crash_and_does_not_fire` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 0 error(s), 3948 warning(s), 219 waived
- error-findings: none (measured, zero errors)
