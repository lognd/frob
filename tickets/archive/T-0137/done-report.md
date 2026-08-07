## Done report

**Root cause**: `frob:tests` is written on EITHER endpoint in this
codebase -- above the source symbol naming the covering test as its
target (e.g. `src/frob/strata/_sysdoc.py` above `merge_models`,
`src/frob/gates/__init__.py` above `sys_gate`), or above the test naming
what it covers as its target (`frob.gates`'s own `_test_edges`
convention, and every fixture `tests/test_testing.py::TestSelect` already
had). `src/frob/testing/_select.py`'s old `_test_edge_matches`/
`_select_from_edges` assumed a single fixed direction (`edge.target` is
always the source, `edge.src` is always the test) and unconditionally
added `edge.src` to `selected` whenever `edge.target` looked touched.
When a brand-new test file is part of the diff, EVERY method it defines
counts as "touched" (its own hunk covers the whole file) -- including the
test symref that happens to be the `target` of a reversed-direction
edge. That made the reversed edge's `src` (the SOURCE symbol, e.g.
`merge_models`, `sys_gate`) look "selected," and it flowed straight into
`{ids}` -> `pytest -q ... src/frob/strata/_sysdoc.py::merge_models ...`,
which pytest cannot collect, tanking the whole xdist run with exit 5 even
though every real test passed in isolation. Reproduced against
`uv run frob test --base 1b1629e` before the fix (see the two bogus
node ids `src/frob/gates/__init__.py::sys_gate` and
`src/frob/strata/_sysdoc.py::merge_models` in the captured argv).

**Fix seam chosen**: fixed selection itself (`src/frob/testing/_select.py`),
not a render-seam filter in `_runners.py` -- filtering at render would
have silently dropped legitimately-selected fallback package/suite
entries too (those also lack `::`/test-file shape) and would not have
fixed `_collect_unbound`'s parallel direction-blindness
(`_file_has_selected_test`), which could still wrongly apply the
`fallback` policy to a file that already had a bound test. Added
`_looks_like_test_symbol` (a symref is a test if its file path is a
conventional test file, OR its qualname's leading component is `tests`
-- covering Rust's inline `mod tests { ... }` convention, e.g.
`strata-core/src/parse/mod.rs::tests.some_case`, which is neither a
`tests/`-rooted file nor `test_`-prefixed) and `_edge_test_and_source`
(picks whichever endpoint looks like a test as the thing to select, the
other endpoint as what must be touched to trigger it; `None` -- logged
and skipped, never guessed -- when neither or both endpoints look like a
test). `_select_from_edges` and `_file_has_selected_test` both route
through this direction-agnostic resolution now; only the resolved test
endpoint is ever added to `selected`.

**Files touched**: `src/frob/testing/_select.py` (`_edge_symref_path`,
`_looks_like_test_symbol`, `_edge_test_and_source`,
`_source_matches_touched` new; `_select_from_edges` and
`_file_has_selected_test` rewritten to use them; `_test_edge_matches`
removed, folded into `_source_matches_touched`), `tests/test_testing.py`
(`TestSelect.test_reversed_directive_never_selects_the_source_symbol`,
new regression test -- confirmed it fails against the pre-fix code via a
temporary revert/rerun, then passes against the fix), `docs/modules/
testing.md` (Selection algorithm's step 3 rewritten to describe the
direction-agnostic resolution and why it matters), `tickets.md` (this
ticket, created since T-0137 had only been referenced/reserved by prior
dispatches, never actually filed).

**Evidence (CLI)**: 9 pytest node ids recorded via `frob ticket evidence
T-0137 ...` (all of `TestSelect`'s 9 cases, including the new
regression), ledger's `evidence:` list above reflects it. Collection had
to be run with `tests/unit/strata/test_kernel_properties.py` and
`tests/unit/strata/test_threat.py` moved aside for the duration only,
then immediately restored -- both fail to import in this install
independent of this ticket (`ModuleNotFoundError: strata_core` /
`ImportError: cannot import name 'check_effect_completeness'`, the same
pre-existing collection poisoning noted in T-0110's round-2 Done report)
and would otherwise abort `pytest --collect-only` for the whole repo,
which `frob ticket evidence` depends on.

**Exact numbers**: `uv run pytest -q tests/test_testing.py` -> 39 passed
(38 pre-existing + 1 new), same pre-existing `PytestCollectionWarning`
(unrelated, `TestingError`/`TestPolicy` look like test classes to
pytest's collector by name). `uv run pytest -q` (full repo) -> 283
`FAILED` + 4 `ERROR`, byte-identical set (diffed) to a `git stash`
baseline run with none of this ticket's changes applied -- zero
regressions, all pre-existing (native `strata_core`/`frob_core`
extensions unavailable in this install, T-0133/T-0134). `uv run frob
test --base main` -> real touched-set selection (`touched=12 ripple=0
selected_langs=1 unbound=2`), `pytest -q tests/integration/
test_interfaces.py::TestInterfaces::test_testing_collect
tests/test_testing.py`, `exit=0`, `[PASS] python 1.56s` -- no bogus
source-symbol node ids, the exact failure mode this ticket fixes.
`uv run frob test --base 1b1629e` (the wider historical repro) also now
exits 0 with a real selection (confirmed manually; not re-recorded as
ticket evidence since `--base main` is the required verification).

**Gates**: `uv run ruff check` / `uv run ruff format --check` -- clean on
all 3 touched files. `uv run ty check` -- clean (the 4 diagnostics
`uv run frob check --ticket T-0137` reports are pre-existing,
unresolvable `strata_core`/`frob_core` native-extension imports in
`tests/unit/strata/test_capacity.py`, `test_kernel_properties.py`,
`test_threat.py`, `tests/unit/test_dup_core.py` -- none in this ticket's
scope). `frob check --ticket T-0137` otherwise: `ruff-check`,
`ruff-format`, `frob-cycle`, `frob-dup`, `frob-arch`, and every
`frob-exports(*)` PASS; the `gates` FAIL is the pre-existing repo-wide
baseline (969 violations, 49 waived, mostly PERF00x/TEST00x/COV00x noise
across files this ticket never touched) with two additions from this
ticket's own new test: one PERF003 (a `next()` lookup plus a `not any()`
assertion in the new regression test, same shape as several already-
waived PERF003s elsewhere in this file) -- waived with `frob:waive
PERF003 reason="a next() lookup plus a not-any() assertion, not a nested
join"` matching the file's existing idiom -- and one `long-function`
WARN (31 lines vs. the 30-line threshold), left unwaived because several
other pre-existing, unwaived test functions in this exact file already
exceed the threshold by more (`test_select_and_run_in_linked_worktree`
35 lines, `test_parses_node_ids_and_caches_on_content_hash` 32 lines),
so it is not a new class of finding, just one more instance of an
already-tolerated repo pattern. No other unwaived violations attributable
to any file this ticket touched. Not closed, not committed, per
instruction.
