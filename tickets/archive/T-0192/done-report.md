## Done report

Survey premise correction: the CLI surface itself (`--probe` flag on `frob
dup`, `dup_probe` config field, `_probe`/`dup_runner.run` dispatch, and a
CLI-level subprocess test `test_cli_probe_equivalent_functions`) already
landed in commit `7b748bea71fd0372e8e32c92c865637c6f6e8a0e`
("feat(dup): wire frob dup --probe for R6 observational equivalence",
frob:ticket T-0041) before this worktree's base -- reachable and passing
in a fresh `make core` build. The T-0192 survey that filed this ticket ran
against a tree that predates that landing. What was still genuinely
missing, and what this ticket did:

- `docs/modules/dup.md`'s R6 implementation note (lines ~254-272) still
  said "wiring an actual `frob dup --probe` CLI flag is out of
  `frob.dup`'s scope and reported to the coordinator" -- stale, since the
  flag exists. Replaced with an accurate description of the CLI surface
  (path resolution, cache/graph build, 30s fixed budget, exit codes) and
  a loud, explicit safety/workload-contract paragraph: the purity
  heuristic only inspects the two probed functions' body tokens, but
  `_load_python_callable` (`src/frob/dup/_pipeline.py`) loads each
  candidate via `importlib.util.spec_from_file_location` +
  `spec.loader.exec_module(module)`, which executes the ENTIRE source
  file's top-level code, not just the probed function -- no sandbox, no
  subprocess isolation, arbitrary repo-controlled code runs with the
  `frob` process's own privileges. Verified this by reading
  `_load_python_callable`/`_probe_callables` in `_pipeline.py` directly.
- `src/frob/__main__.py`'s `--probe` argparse help text repeated only "R6:
  probe two symbols for observational equivalence (pure only)" with no
  hint that it executes code. Rewrote the help text to state the
  execution/sandbox fact and point at the doc.
- `src/frob/app/dup_runner.py`'s `_probe` had no docstring beyond a
  one-liner; added the same warning to its docstring.
- Added `frob:ticket T-0192` directives on `_add_dup_parser` (__main__.py)
  and `_probe` (dup_runner.py) alongside the existing T-0041 directives,
  since both were touched under this ticket.
- No source-code behavior change to `probe_equivalence`/`_probe`/the
  argparse wiring itself -- it was already correct and already tested at
  the CLI level; this pass is documentation-and-help-text honesty about a
  safety property that existed but was not surfaced to the operator.

Changed:
- docs/modules/dup.md (R6 implementation note: stale scope claim ->
  accurate CLI description + safety/workload contract)
- src/frob/__main__.py (`_add_dup_parser`: `--probe` help text now states
  the execution/sandbox fact; added `frob:ticket T-0192`)
- src/frob/app/dup_runner.py (`_probe`: docstring now states the
  execution/sandbox fact; added `frob:ticket T-0192`)

Evidence:
- `tests/test_dup_rungs.py::test_cli_probe_equivalent_functions` -- real
  subprocess (`python -m frob dup <tmp_path> --probe src/m.py::da
  src/m.py::db`) against two genuinely-equivalent pure functions in a
  throwaway repo; asserts `EQUIVALENT` in stdout/stderr and returncode 0.
  Ran directly: `uv run pytest
  tests/test_dup_rungs.py::test_cli_probe_equivalent_functions -v` ->
  `1 passed in 2.21s`. Node id confirmed via `pytest
  tests/test_dup_rungs.py --collect-only`.
- Full `tests/test_dup_rungs.py` (12 tests, including the 6
  `probe_equivalence`-unit tests already bound via existing `frob:tests`
  directives) -- `uv run pytest tests/test_dup_rungs.py -q` -> all 12
  passed.
- `uv run frob dup --help` -- manually confirmed the new warning text
  renders in the actual CLI help output.
- `uv run ruff check src/frob/__main__.py src/frob/app/dup_runner.py` and
  `ruff check` (both PATH and project-pinned) -- both clean, no
  discrepancy.
- `uv run ty check src/frob/app/dup_runner.py src/frob/__main__.py` --
  clean.

Filed: none. No out-of-scope work discovered.

Gates: `uv run frob check --delta --ticket T-0192` clean after a fresh
`frob ticket sweep T-0192` (pre-work sweep was stale from a prior `make
core` run touching Cargo.lock, which was reverted -- see below):
`gates 0/3 new  0 violation(s), 27 waived` -- the 27 waived are
pre-existing repo-wide waivers untouched by this ticket, not new. The
`git diff main --diff-filter=D --stat` land-rule check (agent-playbook.md
section 9) is empty -- no unintended deletions.

Note: `make core` regenerated `frob-core/Cargo.lock` and
`strata-core/Cargo.lock` as a build side effect; both reverted with `git
checkout` since they are outside T-0192's scope and carried no
substantive change.
