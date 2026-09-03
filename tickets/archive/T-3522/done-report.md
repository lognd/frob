## Done report

Changed:
- src/frob/tickets/_reconcile.py::reconcile
- src/frob/app/ticket_runner/_query.py::_save_unlanded_summary_cache
- tests/test_ticket_reconcile.py (2 new tests)
- docs/modules/tickets-lifecycle.md (Unlanded branch work section)

Wired `_save_unlanded_summary_cache` into `reconcile`, right after
`_unlanded_branch_work` computes the branch findings, matching the
production write path `_save_unlanded_summary_cache`'s own docstring
already documented but that was never actually added -- `frob ticket
doable`'s TTL summary cache was previously populated only by tests.
Removed the now-stale DEAD001 waiver from `_save_unlanded_summary_cache`
and updated both functions' docstrings plus
docs/modules/tickets-lifecycle.md to describe the real caller and
clarify the cache write happens on both dry-run and apply (a
best-effort performance cache under `.frob/`, not ticket state).

Evidence:
- tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork::test_populates_the_doable_summary_cache (pytest node id, verified passing)
- tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork::test_populates_the_cache_even_on_a_dry_run (pytest node id, verified passing)

Filed: none

Gates: `uv run frob test --base main` clean (11 python tests recorded).
Scoped `frob check --ticket T-3522 --only affect_drift --only coverage
--only fmt` clean on this ticket's own touched-set concerns (no
AFFECT001 on `reconcile` after the docs update, no new COV002/TODO001
on touched files); repo-wide FAIL lines from unscoped families (WAIVE,
DRIFT, etc.) are pre-existing per the run's own scope note and
unrelated to this change (e.g. WAIVE009/010 on
src/frob/arch/_normalized.py, a file this ticket never touched).
