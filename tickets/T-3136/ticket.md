---
id: T-3136
title: verify_pytest_collect passes non-Python touched files straight to pytest, false-refusing
  rc=4
state: done
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/refactor/_verify.py
- docs/commands/refactor.md
- tests/test_refactor.py
evidence_scope:
- tests/test_refactor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/commands/refactor.md
  reason: 'Doc-anchor and evidence-covered test file for the fix, per SCOPE001/SCOPE002.

    '
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/test_refactor.py
  reason: 'Doc-anchor and evidence-covered test file for the fix, per SCOPE001/SCOPE002.

    '
  actor: logan
  at: '2026-08-27'
evidence:
- tests/test_refactor.py::TestVerify::test_pytest_collect_skips_non_python_touched_files
- tests/test_refactor.py::TestVerify::test_pytest_collect_passes_when_all_touched_files_non_python
designated_repro_test: tests/test_refactor.py::TestVerify::test_pytest_collect_skips_non_python_touched_files
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: fb11afe83bf07e2a7480eecb4aa0ca97f9852db3
---
MEASURED 2026-08-27, T-3086 attempt 5 (after T-3066/T-3105/T-3109/T-3122
all landed). Ran the exact split from T-3086's own brief:

    frob refactor split frob.gates._models \
      --symbols Severity,WaiverRef,DebtEntry,Violation \
      --into frob.findings

With --skip-pytest-collect the split applied cleanly (56 ops across 44
files), committed, and BOTH `import frob.gates._models` and `import
frob.findings` succeed -- import_resolution and module_import (T-3119)
both PASS. This is a DIFFERENT, FIFTH defect: without
--skip-pytest-collect, the chunk's own `pytest_collect` Verify-phase
check fails with `rc=4` (pytest's own USAGE_ERROR exit code), correctly
triggering rollback (the existing rollback machinery works -- this is
NOT a repeat of any of T-3066/T-3105/T-3109/T-3122).

ROOT CAUSE: `verify_pytest_collect` (src/frob/refactor/_verify.py) is
called with `targets=touched_files` (via `_run_chunk_verify` /
`run_verify_outcomes`'s `pytest_scope_touched_only=True`), and
`touched_files` is the FULL set any `RefactorPlan.reference_ops` entry
rewrote -- NOT filtered to `.py` files. This split's plan touched
`docs/design/check-fix-engine.md` (a prose citation of the moved
symbols' old symref, T-1267's carrier). `verify_pytest_collect` passes
EVERY touched file, non-Python included, straight onto pytest's own
command line as a collection target with no filter:

    args = ["pytest", "--collect-only", "-q", "-p", "no:cacheprovider"]
    if targets:
        args.extend(str(t) for t in targets)

pytest then refuses outright (`ERROR: not found: .../docs/design/
check-fix-engine.md (no match in any of [<Dir design>])`, exit 4) the
instant a non-Python path is one of its targets -- a hard usage error,
not a collection failure of any REAL test, and completely unrelated to
whether the split itself is correct.

CONFIRMED BY: reproducing the exact command `verify_pytest_collect`
built, against the plan's own 44 touched files (via `git show --stat`
on the (reset) wip commit) --
`uv run pytest --collect-only -q -p no:cacheprovider <44 touched paths
including docs/design/check-fix-engine.md>` -> `ERROR: not found:
.../docs/design/check-fix-engine.md ... exitstatus=4`.

CONTRAST with `verify_import_resolution`: that function ALREADY has
this exact filter (T-1885's own fix, `_parse_touched_python_files`
skips `path.suffix != ".py"` and records the skip in
`VerifyOutcome.skipped` rather than ever handing a non-Python path to
`ast.parse`). `verify_pytest_collect` was never given the equivalent
filter -- it hands EVERY touched file straight to pytest's argv
unconditionally.

This is NOT specific to `split`: `_commit.run_verify_outcomes` is the
SAME function `run_refactor`/`run_move_module` also call with their own
`touched_files`, so any single `move`/`rename` whose plan touches a
non-Python carrier (a `tickets/<id>/ticket.md` evidence citation, a
`docs/**` prose mention, a `docs/design/registry/*.yaml` cross-ref --
every one of T-1199/T-1200/T-1267's own carrier kinds) with
`run_pytest_collect=True` (the default) hits the identical false
refusal, not just `split`.

Per the standing per-attempt directive, this was NOT hand-edited
around: the worktree was reset (`git reset --hard` to the pre-split
commit) and this ticket filed instead. T-3086 itself is failed with
this as the blocking finding -- do not retry it until this lands.

This is the FIFTH distinct, independent `frob refactor` defect found in
this drive (after T-3066/T-3105/T-3109/T-3122), all found by the same
one real extraction attempt repeated across landed fixes.

## Plan

Filter `touched_files` to `.py` paths before building `verify_pytest_
collect`'s argv (mirroring `_parse_touched_python_files`'s own `path.
suffix != ".py"` filter), recording the skipped non-Python paths in the
returned `VerifyOutcome` the same way `import_resolution` already
discloses them (never silently dropped). If EVERY touched file is
non-Python, the check should pass-with-note (nothing to collect), not
refuse -- matching `verify_import_resolution`'s own empty-`trees` shape.