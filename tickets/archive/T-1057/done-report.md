## Done report

Traced the [Errno 2] failure to its real origin before touching anything:
`frob.tickets._land.land()` already resolves both `root`/`worktree`
internally at its own top (`root, worktree = root.resolve(),
worktree.resolve()`), so a relative --worktree path is NOT what breaks
land() itself. The break is one layer up, in
src/frob/app/ticket_runner.py's `_land()` CLI wrapper: it reads
`cfg.ticket_worktree` (still relative, since nothing had resolved it yet)
and passes that UNRESOLVED value into `_shared_check_spawn_fn(worktree,
cfg.ticket_id)` BEFORE `land()` is ever called. That closure spawns
`_python_for_tree(root)` (`root / ".venv" / "bin" / "python"`, root=the
still-relative worktree path) via `subprocess.run(..., cwd=root)` --
exactly the observed reproduction, since a relative executable argument
is resolved against the CALLING process's cwd, not the subprocess's
target `cwd=`, so it only worked when the invocation cwd happened to
match.

The ticket's own acceptance text names the fix location as "argument-
parse time". That point is src/frob/app/config.py's
`AppConfig.from_external`, the single place every `Path`-typed CLI arg
(including `ticket_worktree`, fed from `--worktree` in `__main__.py`) is
converted from raw argparse strings -- not `src/frob/tickets/_land.py`,
whose own resolve was already correct. Widened this ticket's scope to
add src/frob/app/config.py (and, once AFFECT001 fired on the edited
`AppConfig`/`from_external` symbols, docs/modules/app.md) via `frob
ticket scope T-1057 --add ... --reason ...`/`--reason-file`, recorded in
the ticket's scope_changes audit trail, rather than silently touching
files the ticket did not declare.

Fix: after the existing generic Path-field loop in `from_external`,
`ticket_worktree` is resolved to an absolute path unconditionally
(`d["ticket_worktree"] = d["ticket_worktree"].resolve()`), so
`_shared_check_spawn_fn`, `land()`'s own internal resolve, and every
other consumer of `cfg.ticket_worktree` see an absolute path regardless
of how `--worktree` was spelled on the command line.

Added a regression test class,
TestLandWorktreeResolvedAtArgParse, covering both a relative --worktree
(asserting `cfg.ticket_worktree` comes back absolute and equal to the
resolved directory) and an absolute --worktree (asserting no behavior
change) by parsing real argparse args through `AppConfig.from_external`,
matching this file's existing `TestLandPushCliWiring` pattern.

Verification: reverted the fix locally and confirmed
tests/test_ticket_land.py::TestLand::test_dry_run_lands_cleanly_and_leaves_no_trace,
::TestMergeConflictOutsideLedger::test_real_conflict_outside_tickets_md_aborts,
and ::TestWipCommitNormalizationOnlyDirty::test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed
fail identically on the pre-fix baseline (stray `.frob/derived.lock`
untracked-file assertion, unrelated to this ticket) before restoring the
fix -- these 3 are pre-existing failures, not caused or fixed by this
change. With the fix applied, the rest of tests/test_ticket_land.py (all
but those 3) passes clean, tests/unit/test_config.py passes clean, and
`frob check --ticket T-1057` is fully green (0 errors) after the
AFFECT001 doc-drift fix above.

### Changed
```
 tickets.md | 50 +++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 49 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ticket_land.py::TestLandWorktreeResolvedAtArgParse::test_relative_worktree_arg_resolves_to_absolute` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandWorktreeResolvedAtArgParse::test_absolute_worktree_arg_unchanged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 2221 warning(s), 377 waived
- error-findings: none (measured, zero errors)
