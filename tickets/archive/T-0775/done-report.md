## Done report

Changed:
src/frob/perf/_loop_effects.py (new: PERF008 detector, `loop_invariant_effect_violations`, `_EffectGraph`)
src/frob/perf/_rules.py (wire PERF008 into `perf_rules`)
src/frob/perf/__init__.py (export `loop_invariant_effect_violations`, docstring update)
docs/modules/perf.md (PERF008 rule-table row + new section)
tests/unit/perf/test_loop_effects.py (new: 5 true/false-positive cases)
tests/test_perf_loop_invariant_effect_lock.py (strict xfail lock removed per its own docstring's instruction now that PERF008 lands; assertion pinned to `v.rule == "PERF008"`)

Implemented PERF008 (`frob.perf._loop_effects.loop_invariant_effect_violations`):
a loop-invariant effectful-call detector wired into `perf_rules`, per T-0775's
acceptance. Detection walks each python file's raw tree-sitter AST for
for/while loops, attributes each call site to its innermost enclosing loop,
and checks two things: (1) is the call directly, or transitively (via a
second local, whole-project, name-based call graph -- `_EffectGraph`,
deliberately NOT `frob.graph.callgraph.build_call_graph`, which only resolves
PRIVATE callees by design and would miss the real T-0773 incident's public
`frob.gitio.run_argv` boundary), a process-spawn/directory-walk effect; (2)
does the call's own argument text avoid the loop's bound variable(s) and any
name assigned in the loop body. Both true fires PERF008 (WARN, waivable with
a reasoned `frob:waive PERF008`).

Verified against the real repo: `frob check --only gates-native` on frob's
own tree fires PERF008 (as warnings; gate still passes) on real hits
including `src/frob/tickets/_land.py`'s `_rev_parse` transitively reaching
`guarded_subprocess_run` -- the live analogue of the T-0773 incident.

Scope was widened twice via `frob ticket scope --add` (both recorded above
in `scope_changes`): `docs/modules/perf.md` (COV001 needs a `frob:doc`
anchor for the new public symbol) and
`tests/test_perf_loop_invariant_effect_lock.py` (a pre-existing strict
xfail lock whose own docstring instructs removing the marker and pinning
the assertion to the new rule id once the detector lands -- done).

Cuts: PERF008 is Python-only (matching PERF001-004's existing
python-first/other-language-best-effort tiering), tracked as a
`frob:todo T-0775` in `_loop_effects.py`'s module docstring rather than
silently expanding this ticket to cover typescript/rust/cpp too.

Evidence: `tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect` (5 node ids, all passing: `test_fs_walk_direct_call_in_loop_is_flagged`, `test_loop_invariant_spawn_call_two_hops_deep_is_flagged`, `test_ticket_row_rev_parse_shape_fires_on_real_repo_history_fixture`, `test_loop_varying_argument_is_not_flagged`, `test_no_effectful_call_in_loop_is_not_flagged`) plus `tests/test_perf_loop_invariant_effect_lock.py::test_loop_invariant_spawning_callee_in_loop_is_flagged` -- all 6 observed passing via `pytest --collect-only` + a foreground run; also `frob test --base main` selected and passed 21 python test(s) (touched-set, includes pre-existing `tests/test_perf.py` PERF001-004/007 suite unaffected).

Filed: none.

Gates: `frob check --only lint/gates-fast/gates-native/gates-security --ticket T-0775` all `pass`/0 errors (gates-native shows PERF008 firing as WARN on real pre-existing repo call sites, which is the detector working as designed, not a regression -- gate:PERF stays `pass`). Pre-existing `gate:SELFAUDIT` (5 errors, `src/frob/arch/_logging_checks.py`) and `gate:SYS`/`gate:TEST`/etc. warnings are untouched debt outside this ticket's scope (confirmed via `git diff main -- src/frob/arch/_logging_checks.py` showing no change from this worktree). `git diff main --diff-filter=D --stat` is empty (deletion-filter land rule, section 9).
