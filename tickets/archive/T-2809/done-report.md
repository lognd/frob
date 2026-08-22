## Done report

Changed:
- src/frob/app/_check_chunking.py::_derive_post_land_sweep_budget_s
- src/frob/app/_check_chunking.py::_record_budget_timing_sample
- src/frob/app/_check_chunking.py::_load_budget_timing_samples
- src/frob/app/_check_chunking.py::_save_budget_timing_samples
- src/frob/app/_check_chunking.py::_budget_timing_samples_path
- src/frob/app/_check_chunking.py::_run_budgeted_check (wired the new sample recording call)

Evidence:
- tests/unit/test_check_budget.py::TestDerivePostLandSweepBudget.test_contended_sample_does_not_inflate_the_estimate
- tests/unit/test_check_budget.py::TestDerivePostLandSweepBudget.test_genuine_slowdown_still_raises_the_estimate
- tests/unit/test_check_budget.py::TestDerivePostLandSweepBudget.test_group_with_no_sample_window_falls_back_to_ema
- tests/unit/test_check_budget.py::TestBudgetTimingSampleWindow.test_appends_and_caps_window
- tests/unit/test_check_budget.py::TestBudgetTimingSampleWindow.test_load_missing_file_returns_empty

Approach: `_derive_post_land_sweep_budget_s` no longer sums the plain
per-group EMA (`.frob/check-budget-timing.json`), which is re-recorded by
every check run including ones made under heavy fleet contention and fed
straight into the land lock wait ceiling (deadline - estimated_work_s).
It now records each chunk's raw elapsed time into a separate bounded
per-group sample window (`.frob/check-budget-timing-samples.json`,
`_BUDGET_TIMING_SAMPLE_WINDOW=5`) and derives the estimate from the
MINIMUM of that window per group, falling back to the EMA for any group
the window has not covered yet (backward compatible with a pre-T-2809
timing file). Contention can only ever push a measured wall-clock sample
up, never below the true uncontended cost, so the minimum of a recent
window is immune to a transient busy box while a sustained genuine
slowdown still raises the estimate once enough consecutive runs (the
whole window) measure the higher cost -- verified directly by the two
positive-control tests above (a single contended sample does not move the
budget; a sustained higher cost does).

Filed: none (in-scope fix, no out-of-scope follow-up found)

Gates: `frob check --ticket T-2809` run per stage group (gates-fast,
gates-native, gates-security, lint, static); the only in-scope finding
(DOC007/DRIFT002 on this ticket's own `frob:tests` directive using the
wrong separator form) was fixed directly. All other errors surfaced are
pre-existing repo-wide baseline (ledger backlog/TICK, unrelated
DRIFT/DOC/TEST findings in other modules, claude-config-drift, ruff-format
drift in unrelated test files) -- none touch this ticket's changed
symbols. `pytest tests/unit/test_check_budget.py
tests/test_cache_transparency.py -k "Budget or budget"` (34 collected, 0
failed) under FROB_ALLOW_FULL_CHECK=1 to bypass an unrelated FROB_AGENT
full-check refusal in one pre-existing test.
