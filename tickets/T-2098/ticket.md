---
id: T-2098
title: 'make -n coverage-fast is not a dry run: the recursive-make line really executes
  frob ticket reconcile --apply against the shared root, and hangs'
state: done
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- Makefile
- tests/test_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_coverage.py::TestMakeDryRunDoesNotExecuteMutatingCommands::test_dry_run_coverage_fast_completes_quickly
- tests/test_coverage.py::TestMakefileNoCompoundRecursiveMake::test_no_recipe_line_combines_dollar_make_with_other_commands
- tests/test_coverage.py::TestCoverageTargetNativesGuard::test_coverage_fast_incremental_branch_restores_and_verifies_natives
designated_repro_test: tests/test_coverage.py::TestMakeDryRunDoesNotExecuteMutatingCommands::test_dry_run_coverage_fast_completes_quickly
acceptance:
- text: given make -n is invoked on any target, when it completes, then no mutating
    frob command has run against the shared root -- verified by comparing git status
    --porcelain before and after; this test MUST fail against current main
  evidence:
  - tests/test_coverage.py::TestMakeDryRunDoesNotExecuteMutatingCommands::test_dry_run_coverage_fast_completes_quickly
  - tests/test_coverage.py::TestMakefileNoCompoundRecursiveMake::test_no_recipe_line_combines_dollar_make_with_other_commands
- text: given tests/test_coverage.py runs, when the natives-guard test executes, then
    the whole file completes and reports a pass/fail summary rather than stalling
    -- all 44 tests measured
  evidence:
  - tests/test_coverage.py::TestCoverageTargetNativesGuard::test_coverage_fast_incremental_branch_restores_and_verifies_natives
- text: given the _dry_run helper docstring claims none of the commands are executed,
    when the claim is re-read after the fix, then it is true or has been corrected
    to state the $(MAKE) exception
  evidence:
  - tests/test_coverage.py::TestMakefileNoCompoundRecursiveMake::test_no_recipe_line_combines_dollar_make_with_other_commands
threat: null
component: testing
labels:
- fleet-blocking
anchor: false
anchor_reason: null
land_commit: null
---
## Measured

`tests/test_coverage.py` cannot complete. Four tests pass, then
`TestCoverageTargetNativesGuard::test_coverage_fast_incremental_branch_
restores_and_verifies_natives` (line 241) stalls in `subprocess.run` via the
helper `_dry_run` (line 179) and is killed by the per-test timeout. That is
why all 44 tests in the file were reported UNMEASURED in the full-suite
sweep.

Reproduced directly, outside pytest:

    $ time timeout 120 make -n coverage-fast >/dev/null 2>&1
    real 2m3.601s
    exit=124                       # killed, did not complete

Target-specific, not Makefile-wide:

    make -n clean   -> OK
    make -n core    -> OK
    make -n coverage-fast -> hangs

## Root cause

`Makefile:406-408`:

    coverage-fast: $(STAMP)
        $(MAKE) core && uv run frob ticket reconcile --apply && uv run frob doctor || exit 1
        uv run frob coverage .

GNU make executes any recipe line containing `$(MAKE)` EVEN UNDER `-n`, so
that sub-make can be traced. That is standard, documented behaviour -- but
the line is a compound `&&` chain, so the whole thing runs, not just the
sub-make. `make -n coverage-fast` therefore really executes:

    uv run frob ticket reconcile --apply      # a MUTATING ledger write
    uv run frob doctor

against the SHARED ROOT.

The test helper's own docstring asserts the opposite
(`tests/test_coverage.py:175-179`):

    """`make -n <target>` output: the exact shell commands `make` WOULD
    run, in order, with none of them actually executed -- safe to call
    from a test."""

"none of them actually executed" and "safe to call from a test" are both
false for any line containing `$(MAKE)`. There are three such lines
(Makefile:317, 320, 407).

## Why this is more than a slow test

`frob ticket reconcile --apply` mutates the ticket ledger in the shared
root. A dirty shared root DirtyMain-blocks EVERY agent land in the fleet --
that has already cost this session a finished ticket's land and required
manual recovery. A test suite that silently runs a mutating ledger command
against the shared root is a fleet hazard, not just a hang. (Root happened
to be clean after my probe, but that is luck about timing, not a guarantee.)

## Hypothesis for the hang -- explicitly NOT a claim

`frob ticket reconcile` is a ticket verb, so it goes through the dispatch
path, which calls `refuse_if_land_in_progress`
(`src/frob/app/ticket_runner/__init__.py:653`). That function has a
confirmed poll loop that does not observe its exit condition -- T-2093,
critical, three tests hang on exactly that line. If the two are the same
defect, T-2093's fix resolves this hang too and this ticket is then only
about the dry-run-is-not-dry hazard. VERIFY before assuming; do not fold
this into T-2093 without evidence.

## DO NOT FIX IT THIS WAY

- **Do not fix it by giving the test a longer timeout.** The problem is not
  duration; it is that a "dry run" performs real mutating work.
- **Do not fix it by marking the test skip/xfail.** It is the only thing
  currently reporting this, and the gate floor reads zero.
- **Do not split the `&&` chain so only `$(MAKE) core` runs under `-n`.**
  That makes the immediate symptom go away while leaving the general trap:
  the next person who adds `$(MAKE)` to a compound line reintroduces it.
- **Do not have the test stop using `make -n`** without addressing that
  `make -n` is genuinely unsafe here. Other callers (human or agent) will
  reasonably assume `-n` is a dry run.

## Relevant standing direction

There is a standing directive that workflows belong in `frob` subcommands
rather than GNU-make recipes, tracked as the T-1382 epic (24 targets
classified: 15 already have a frob equivalent, 4 need one, 5 to
delete/keep). A `make -n` that silently mutates the shared ledger is direct
evidence for that migration. Consider whether the right fix here is removing
this target's dependence on a recursive-make line rather than patching
around it.

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
