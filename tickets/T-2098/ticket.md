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