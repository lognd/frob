## Done report

Changed:
- src/frob/tickets/_reconcile.py::_frob_dir_is_gitignored (new), reconcile
- tests/test_ticket_reconcile.py (_gitignore_frob_dir helper + 1 new test + 2 existing tests updated)
- docs/modules/tickets-lifecycle.md

Root cause: T-3522 wired `_save_unlanded_summary_cache` into `reconcile()`
unconditionally. windows-latest run 33370059331 measured (linux,
fully reproducible, not flaky) that `tests/unit/test_reconcile_auto_
commit_t1936.py::TestReconcileAutoCommit::test_apply_leaves_the_ledger_
clean` and `TestReconcileRemoveOrphansAutoCommit::
test_apply_with_remove_orphans_still_leaves_ledger_clean` both failed:
`git status --porcelain` showed `?? .frob/unlanded-summary-cache.json`
after `reconcile(apply=True)`. The T-1936 fixture repo has no
`.gitignore` at all; every OTHER `.frob/` writer in this test suite
only appears clean there because an EARLIER `git add -A` in the same
test's own setup already staged and committed it as tracked content
before the write under test runs -- not because `.frob/` is genuinely
ignored. A first-time write to a brand-new path (this cache file) has
no such accidental cover.

Fix: `_frob_dir_is_gitignored(root)` (`git check-ignore --quiet
.frob/` -- note the trailing slash: `git check-ignore` on a
nonexistent path with no trailing slash reports "not ignored" even
when a `.frob/` pattern would match, a real quirk measured directly)
gates the cache write. A skip is best-effort and silent-but-logged
(debug), matching `_save_unlanded_summary_cache`'s own existing log-
and-swallow posture -- `reconcile` itself still succeeds either way.
Every real frob-managed repo already gitignores `.frob/` (this
project's own mandated `.gitignore` template), so this only actually
changes behavior against a bare fixture that has not set that up.

Updated the two existing T-3522 cache-population tests to set up
`.gitignore` explicitly via a new `_gitignore_frob_dir` fixture helper
(matching a real repo's own precondition) and added a new regression
test proving the write is skipped -- and nothing is left untracked --
when that precondition is absent.

Evidence:
- tests/unit/test_reconcile_auto_commit_t1936.py::TestReconcileAutoCommit::test_apply_leaves_the_ledger_clean (verified passing, 3x)
- tests/unit/test_reconcile_auto_commit_t1936.py::TestReconcileRemoveOrphansAutoCommit::test_apply_with_remove_orphans_still_leaves_ledger_clean (verified passing, 3x)
- tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork::test_skips_the_cache_write_when_frob_dir_is_not_gitignored (verified passing)
- tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork::test_populates_the_doable_summary_cache (verified passing)
- tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork::test_populates_the_cache_even_on_a_dry_run (verified passing)

Filed: none

Gates: `uv run pytest -p no:xdist tests/unit/test_reconcile_auto_commit_t1936.py tests/test_ticket_reconcile.py` clean (28 passed); the two originally-broken tests re-run 3x locally per the coordinator's instruction, all green. Scoped `frob check --ticket T-3567 --only affect_drift --only coverage --only fmt` clean on this ticket's own touched-set concerns (no AFFECT001/COV002/TODO001/FMT001 against any touched file, after updating docs/modules/tickets-lifecycle.md for the AFFECT001 finding the reconcile() change raised).
