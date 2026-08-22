## Done report

`make -n coverage-fast`'s recipe used to chain `$(MAKE) core` with
`uv run frob ticket reconcile --apply` and `uv run frob doctor` on one
compound `&&` shell line. GNU make executes any recipe line containing
the literal `$(MAKE)` even under `-n` (documented, needed so a recursive
sub-make can be traced) -- but because the line was compound, the whole
chain ran, including the mutating ledger write, under a supposed dry run.
Reproduced directly: `time timeout 120 make -n coverage-fast` measured
exit=124 (killed after 2m), and `tests/test_coverage.py`'s
`TestCoverageTargetNativesGuard::test_coverage_fast_incremental_branch_restores_and_verifies_natives`
hung on exactly this line, taking all 44 tests in the file down as
UNMEASURED.

Fix: removed `coverage-fast`'s dependence on a recursive `$(MAKE)` line
entirely -- it now runs `uv run frob natives build` directly (the same
command `core:` itself runs), `uv run frob ticket reconcile --apply`,
`uv run frob doctor`, and `uv run frob coverage .` as four separate
recipe lines, none containing `$(MAKE)`. This was the ticket's own
suggested direction (removing the recursive-make dependency, T-1382)
rather than narrowing the `&&` chain, which the ticket explicitly warned
would leave the general trap open for the next `$(MAKE)`-containing
compound line.

To close that general trap mechanically (not just patch this one
instance): added `TestMakefileNoCompoundRecursiveMake`, which statically
scans the Makefile source for any recipe line combining the literal
`$(MAKE)` with another shell command via `&&`/`||`/`;`/`|`, and fails if
one exists -- no `make -n` invocation, so it can never itself hang or
mutate anything.

Also corrected `_dry_run`'s docstring (tests/test_coverage.py), which
claimed "none of them actually executed -- safe to call from a test" --
false for any `$(MAKE)` line. It now documents the real exception (a
lone `$(MAKE)` line recurses safely; a compound one does not) and points
at `TestMakefileNoCompoundRecursiveMake` as the mechanism that keeps that
invariant true going forward.

Updated `_assert_guard_precedes_coverage_cli` (and its docstring) to
check for the literal `frob natives build` command instead of the old
`make core` recursive-trace text, since that text no longer appears in
`coverage-fast`'s dry-run output after the fix.

Verified:
- `git status --porcelain` clean before/after `time timeout 20 make -n
  coverage-fast` -- completed in 0.003s (previously exit=124 after
  being killed at 120s).
- `uv run pytest tests/test_coverage.py -o addopts="" -q`: 51 passed
  (was 44 collected, hanging on test 5, before this fix -- 51 includes
  the 7 new/changed tests this ticket adds).
- `frob ticket evidence T-2098 --check-repro
  tests/test_coverage.py::TestMakeDryRunDoesNotExecuteMutatingCommands::test_dry_run_coverage_fast_completes_quickly
  --base-ref 7dfcd1dae`: FAILED_AT_PARENT (genuine repro against the
  repro-test-alone commit, before the fix commit).
- `frob check --ticket T-2098 --only gates-fast`: gate:PRE clean after
  `frob ticket sweep T-2098` refreshed the pre-work sweep; no new
  errors introduced by this change (repo-wide counts unaffected outside
  this ticket's own scope per the --ticket scope-note).

Not folded in (explicitly out of scope, per the ticket's own note):
whether T-2093's `refuse_if_land_in_progress` poll-loop defect is the
same mechanism behind the observed hang -- not verified either way here,
since this fix makes the hang unreachable regardless of that defect's
own status (the mutating command is simply never invoked under `-n`
anymore).

### Changed
```
 Makefile                 |  27 ++++++++--
 tests/test_coverage.py   | 130 +++++++++++++++++++++++++++++++++++++++++++----
 tickets/T-2098/ticket.md |  18 +++++--
 3 files changed, 155 insertions(+), 20 deletions(-)
```

### Evidence
- `tests/test_coverage.py::TestMakeDryRunDoesNotExecuteMutatingCommands::test_dry_run_coverage_fast_completes_quickly` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestMakefileNoCompoundRecursiveMake::test_no_recipe_line_combines_dollar_make_with_other_commands` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageTargetNativesGuard::test_coverage_fast_incremental_branch_restores_and_verifies_natives` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: none (measured, zero errors)
