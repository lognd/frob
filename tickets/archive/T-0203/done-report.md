## Done report

Changed:
src/frob/gates/__init__.py::perf_gate

Root cause: `perf_gate` (src/frob/gates/__init__.py) parsed every file in
`snapshot.file_hashes` unconditionally, including markdown/toml/json files
that have no registered tree-sitter grammar. Each such file hit
`frob.lang.parse_file` -> `Err(LangError.UnsupportedLanguage)`, producing one
skip line per non-code file at default verbosity -- by-design-unscannable
files were indistinguishable from real parse failures.

Fix: `perf_gate` now filters `snapshot.file_hashes` by extension against
`frob.lang.tree_sitter_extensions()` (the canonical T-0129 extension table,
not a duplicated list) BEFORE calling `parse_file`. Filtered-out files never
reach `parse_file`, so they never produce an UnsupportedLanguage skip; at
most one DEBUG-level count line is logged
(`perf_gate: N file(s) filtered out (no registered grammar)`), only when
N > 0. A file that does carry a registered grammar but still fails to parse
(genuine `ParseFailed`/`IoFailed`/etc.) still reaches `parse_file` and still
gets a visible skip message (bumped from DEBUG to WARNING, since the ticket
requires this message stay visible -- distinct from T-0202's log-level pass,
which is a repo-wide formatting/level sweep untouched by this ticket).

Evidence:
- tests/test_gates.py::TestOptInGates::test_perf_gate_flags_list_membership_in_loop
  (pre-existing, still green)
- tests/test_gates.py::TestOptInGates::test_perf_gate_silences_unscannable_files
  (new -- fixture tree with .py/.md/.toml/.json; asserts zero "skipping
  unparsed"/"UnsupportedLanguage" log lines and that scanning still runs)
- tests/test_gates.py::TestOptInGates::test_perf_gate_still_reports_genuine_parse_failure
  (new -- monkeypatches `frob.lang.parse_file` to return `Err(ParseFailed)`
  for one `.py` file since tree-sitter's python grammar proved too
  error-tolerant to reliably produce a genuine parse failure from source
  text alone; asserts the skip message is still emitted for that file)
- tests/test_gates.py::test_gates_run_gates_integration (pre-existing
  integration path through `run_gates`, still green)

All four collected via `uv run pytest --collect-only -q -o addopts=
tests/test_gates.py` and run via `uv run pytest -q
tests/test_gates.py::TestOptInGates::test_perf_gate_flags_list_membership_in_loop
tests/test_gates.py::TestOptInGates::test_perf_gate_silences_unscannable_files
tests/test_gates.py::TestOptInGates::test_perf_gate_still_reports_genuine_parse_failure
tests/test_gates.py::test_gates_run_gates_integration` -> 4 passed.

Filed: none (no out-of-scope work discovered).

Gates: `uv run frob check --stamp-baseline` (pre-change) recorded 41
pre-existing violations (native-extension-unavailable DRIFT/COV
artifacts in this worktree, matching the documented "Worktree natives
artifact" pattern -- `strata_core` reports unavailable inside the `frob
check` subprocess despite `make core` having run in this worktree) plus
routine waived PERF003/PERF004 hits. `uv run frob check --delta --ticket
T-0203` afterward reports `is_baseline_stale: src/frob/gates/__init__.py
changed since stamp` and degrades to the full set (documented fallback
behavior per docs/guides/agent-playbook.md#6) -- manually diffed the
non-waived violation list against the pre-stamp run and confirmed it is
the same 42 pre-existing DRIFT002/COV003/frob-arch items (none touching
`perf_gate` or the filtering logic added here); zero new PERF-rule or
gates-rule violations attributable to this change. `uv run frob test
--base main` selected `tests/test_gates.py` (touched-set); the run
reports 6 failures, all in `TestSysGate`/`TestCov002StrataModuleCoverage`
-- confirmed identical on a `git stash` of this change against the same
base (same 6 node ids fail either way), i.e. pre-existing
native-extension-unavailable environment artifacts, not caused by this
ticket. `ruff check` and `ruff format --check` clean on both changed
files (both `ruff` and `uv run ruff`). `ty check src/frob/gates/__init__.py`
clean (the repo-wide `frob check`'s "ty: Found 2 diagnostics" line is
unrelated to the changed file -- see the round-2 addendum below for exactly
which two diagnostics these are).

Reviewer round 1 caught an unwaived PRE001 (the recorded pre-work sweep had
gone stale against current scope) that this Done report had not addressed.
Fix: re-ran `uv run frob ticket sweep T-0203` (plain `frob ticket start`
errors `InvalidTransition` on an already-in-progress ticket -- `sweep` is
the correct refresh command) to record a fresh sweep
(`dup_findings=165 xref_hits=4`), then re-ran `uv run frob check --ticket
T-0203` clean of PRE001: the ticket-scoped run reports 14 non-waived
violations, none of them PRE001 and none touching this ticket's scope --
11x COV003 on ticket T-0065 (stale evidence ids on
`tests/unit/strata/test_kernel_properties.py`, a file this ticket never
touched), 1x COV003 on T-0148, 1x COV003 on ticket T-0168 (same pattern on
`tests/test_gates.py::TestConventionUnitBinding::test_test001_exempts_strata_flow_declarations`,
pre-existing before this ticket's edits), and
1x TEST006 (no coverage stamp; TEST006 is campaign-wide and explicitly out
of scope per this ticket's dispatch instructions). No new violations
appeared as a result of the sweep refresh.
(Coordinator note at landing: the round-2 addendum originally listed a
"1x SYS004" entry absent from the actual gate output -- the reviewer's
re-run counted 14 violations with zero SYS004; enumeration corrected here
per the reviewer's named remedy, same phantom-SYS004 pattern as T-0181.)

Also confirming per reviewer request: the 2 `ty` diagnostics
(`Found 2 diagnostics`) are exactly `error[unresolved-import]: Cannot
resolve imported module 'strata_core'` at
`tests/unit/strata/test_capacity.py:351` and `error[unresolved-import]:
Cannot resolve imported module 'frob_core'` at
`tests/unit/test_dup_core.py:30` -- confirmed via `uv run ty check` run
directly. Both are the known frob_core/strata_core worktree-native
artifact: `ty`'s static import resolver does not see the maturin-built
native extensions installed into this worktree's `.venv` (it only
resolves against `site-packages`/first-party source, not the editable
native build), so it flags the two files that `import strata_core` /
`import frob_core` directly even though those imports resolve fine at
runtime (confirmed above via passing pytest runs that exercise the same
natives). Neither file is in this ticket's scope or touched by this
change; `ty check src/frob/gates/__init__.py` in isolation remains clean.
