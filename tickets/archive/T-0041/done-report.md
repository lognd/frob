## Done report

### Sub-item assessment (all three found already implemented pre-session;
verified with file/line evidence, not re-churned)

1. **`frob dup --probe` CLI wiring -- already done.**
   `src/frob/app/dup_runner.py::_probe` (lines 20-37), CLI flag in
   `src/frob/__main__.py::_add_dup_parser` (line ~178, `--probe` ->
   `dup_probe`), `AppConfig.dup_probe: list[str]` at
   `src/frob/app/config.py:81`. All wired to
   `frob.dup.probe_equivalence` before this session touched anything.

2. **Full APTED tree-edit distance -- already done.**
   `frob-core/src/lib.rs::apted_similarity` (line 354, Zhang-Shasha over
   real subtree structure, doc comment at lines 196-211 explaining the
   APTED-class choice). Called from
   `src/frob/dup/_pipeline.py::_apted_similarity_for_pair` (line 529) and
   used as the REPORTED R4 similarity (module docstring lines 30-37); the
   old statement-Levenshtein (`_core.tree_edit_similarity`) is
   deliberately kept only as a near-miss floor / region-span aid, not the
   primary metric. `cargo test` cannot run in this worktree
   (`pyo3-build-config` build script fails: "cannot set a minimum Python
   version 3.11 higher than the interpreter version 3.10" -- same
   libpython-vs-abi3 constraint noted on prior tickets); `make core`
   compiles and installs the extension cleanly (verified this session).

3. **Real CFG/DFG vs co-occurrence proxy -- already substantially done
   post-T-0117; no further genuine gap in this ticket's scope.**
   `_real_dataflow_graph` (`src/frob/dup/_pipeline.py:420`) builds def-use
   edges from real `block`-node AST structure with sequential
   control-flow edges (real execution order), not token co-occurrence.
   Remaining gaps (branch-edge fan-out for if/for/while, true
   reaching-definitions) are explicitly recorded as `frob:todo T-0001`
   follow-up in the module docstring (lines 55-62), not silently dropped.
   `_build_dataflow_graph` (the original proxy) survives only as the
   fallback when no `block` node is found. Extending branch fan-out is a
   separate, larger unit of work than "replace the proxy" (done); not
   implemented here.

### Bug found and fixed while demonstrating sub-item 1 (in scope:
`src/frob/dup/_pipeline.py`)

Demonstrating `--probe` end-to-end on a renamed multi-arg pair (R6's
actual purpose) showed `probe_equivalence` always reporting `DIFFER`.
Root cause: `_run_probe_cases`/`_call_safe` called `fn_b(**kwargs)` using
`fn_a`'s parameter names -- any pair with differently-named parameters
(every real rename) raised `TypeError` on `fn_b`, comparing unequal every
time. Fixed by calling both callables positionally (`_call_safe`,
`fn(*args)`).

### Reviewer-caught regression from that fix (REJECTED, then addressed)

The positional-call fix opened a worse hole: `probe_equivalence(f, g)`
with `def f(*, a, b): return a - b` and `def g(*, x, y): return x + y` --
opposite logic -- reported `equivalent=True cases_run=50`, because both
sides raise `TypeError` under positional calling on every case, and
`_call_safe`'s shared-exception sentinel (`("__frob_exc__", type name)`)
counted the matching `TypeError`s as agreement. This is the vacuous-pass
class the project exists to kill.

Fixed with two guards, both refusing (`Err(NoGenerator)`) rather than
falling through to a verdict, since `_call_safe` cannot distinguish "both
sides legitimately agree" from "both sides can't be called this way":

- `_probe_strategies` (`src/frob/dup/_pipeline.py:1080`) now rejects
  `inspect.Parameter.KEYWORD_ONLY` alongside the existing
  `VAR_POSITIONAL`/`VAR_KEYWORD` rejection -- a keyword-only parameter can
  never legitimately be supplied positionally, so probing it always
  raises on the first case.
- `_probe_arity_compatible` (new, `src/frob/dup/_pipeline.py:1128`)
  checks, via `inspect.Signature.bind` with placeholder values (never by
  calling `fn_b`), that `fn_b` accepts exactly as many positional
  arguments as `fn_a`'s probed parameter count. Reasoned against R6's
  renamed-clone purpose: a differing-arity pair (e.g. 2 required params
  vs 3 required params) hits the identical vacuous-pass shape as the
  kwonly case -- `fn_b(*args)` always raises `TypeError` for arity
  reasons unrelated to logical equivalence -- so it gets the same
  refusal, not a verdict. A pair where the extra parameter has a default
  (bindable with the same positional count) is NOT rejected by this
  guard, since that call is legitimately callable and any behavioral
  difference the default causes is real evidence, not an artifact of
  uncallability.
- `probe_equivalence` (`src/frob/dup/_pipeline.py:1008`) now runs the
  arity check between the strategies-from-`fn_a` step and
  `_run_probe_cases`, refusing before any case is drawn.

### Files changed

- `src/frob/dup/_pipeline.py` -- `_call_safe`, `_run_probe_cases`
  (positional calling), `_probe_strategies` (KEYWORD_ONLY rejection),
  `_probe_arity_compatible` (new), `probe_equivalence` (arity-guard
  wiring); docstrings updated throughout explaining the vacuous-pass
  reasoning.
- `tests/fixtures/dup_rungs/src/mod_r6.py` -- added `sum_twice_a/b`
  (renamed multi-arg pair, regression fixture for the positional-call
  fix), `kwonly_subtract`/`kwonly_add` (opposite-logic kwonly pair,
  reviewer's exact repro), `arity_two`/`arity_three` (arity-mismatch
  pair).
- `tests/test_dup_rungs.py` -- added
  `test_fires_on_equivalent_functions_with_renamed_multi_arg_params`,
  `test_refuses_keyword_only_params_instead_of_vacuous_pass`,
  `test_refuses_mismatched_arity_instead_of_vacuous_pass` (all with
  `frob:tests`/`frob:ticket T-0041` directives).
- `tickets.md` -- widened `scope` to include
  `tests/fixtures/dup_rungs/**` (needed by the fixture additions above).

### Verification

- `tests/test_dup_rungs.py`: **12 passed** (was 9 pre-session, 10 after
  the positional-call fix, 12 after the reviewer's two regression tests)
- Full dup suite (`test_dup_rungs.py`, `test_dup_smart.py`,
  `unit/test_dup.py`, `unit/test_dup_cache.py`, `unit/test_dup_core.py`,
  `unit/test_dup_smt.py`, `system/test_cli_dup.py`): **71 passed, 2
  skipped** (SMT tests skip -- optional `z3-solver` not installed), 0
  failed
- R5 false-positive test
  (`TestR5Dataflow::test_no_false_positive_against_unrelated_function`)
  green after a fresh `make core`
- Reviewer's exact repro (`f(*, a, b): return a - b` vs
  `g(*, x, y): return x + y`), re-run directly against
  `_probe_strategies(f)`: now `Err(NoGenerator)` -- refusal, not a
  vacuous `equivalent=True`
- CLI demo end-to-end (manual, `/tmp/probedemo2`, renamed two-arg pure
  functions): `frob dup <root> --probe src/m.py::total_v1
  src/m.py::total_v2` reports `EQUIVALENT`, `cases_run=50`, exit 0
- `uv run frob check --ticket T-0041`: 83 violations, 17 waived, both
  before and after the reviewer's required changes -- unchanged; only
  pre-existing repo-wide `PERF*`/`TEST002`/`TEST003`/`TEST006`
  diagnostics remain, none touching this ticket's changed files
  unwaived; `SCOPE001`/`PRE001` clean after the scope widening and
  `frob ticket sweep T-0041` re-run

### Out-of-scope findings

None filed -- the probe kwargs/positional bug and its regression were
in-scope (`src/frob/dup/_pipeline.py`) and directly blocked demonstrating
sub-item 1 correctly, so fixed rather than filed. Next free id remains
T-0130 (unused).

### Not touched (per scope boundaries)

`src/frob/strata` (T-0078), `src/frob/graph|outline|xref|testing|policy|arch`
(T-0129).

**Status: T-0041 left `in-progress`, not closed, not committed**, per
instructions. Evidence recorded via `frob ticket evidence T-0041`.
