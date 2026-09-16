## Done report

Root cause: AppConfig.from_args/__main__._dispatch_default read [tool.frob] pyproject.toml config from the invoking process's own CWD, never from the target ticket root a frob ticket <verb> --path <ROOT> (or FROB_ROOT) invocation names. This repo's own pyproject.toml sets ticket_land_branch = dev (T-4496), so any frob ticket land --path <unrelated-tmp-root> run with this repo as CWD silently inherited dev as the unrelated target root's land branch and refused with TargetBranchInvalid the instant that root had no dev branch -- exactly tests/system/test_cli_ticket_land.py::TestLandCLI::test_dry_run_reports_clean, failing on all three CI legs at dev d6cfcaf99. Fix: added AppConfig._pyproject_file_for_args (mirrors ticket_runner._resolve_ticket_root's explicit --path/FROB_ROOT/cwd precedence, T-1674) and routed AppConfig.from_args and __main__._dispatch_default's from_external call through it. Measured: reproduced verbatim pre-fix; post-fix tests/system/test_cli_ticket_land.py (1), test_app_config_from_external_t1276.py + new test_app_config_pyproject_root_t_draft_1f1ae69b.py (13), test_app.py + test_app_config_flag_coverage.py + test_main_entry.py (72) all pass, 0 failed. BUG002 confirmed via --check-repro: FAILED_AT_PARENT at 1eb11481e. ruff check/format clean. Out of scope: same CWD-vs-root gap likely affects other --path subcommands (perf_path/release_path/stats_path/natives_path/mutate_path) -- follow-up ticket recommended.

### Changed
```
 src/frob/__main__.py                               | 16 +++++-
 src/frob/app/config.py                             | 50 +++++++++++++++++-
 ...t_app_config_pyproject_root_t_draft_1f1ae69b.py | 61 ++++++++++++++++++++++
 tickets/T-4502/ticket.md                 | 38 ++++++++++++--
 4 files changed, 159 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/system/test_cli_ticket_land.py::TestLandCLI::test_dry_run_reports_clean` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
