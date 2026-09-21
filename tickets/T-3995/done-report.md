## Done report

-- T-3995

### Changed
```
 docs/commands/check.md          |    9 +
 src/frob/_cli_parsers/_check.py |    9 +-
 src/frob/app/check_runner.py    |   50 +-
 tests/test_check_runner.py      |   82 ++
 tickets/T-3995/done-report.md   | 2303 +++++++++++++++++++++++++++++++++++++++
 tickets/T-3995/ticket.md        |   25 +-
 6 files changed, 2459 insertions(+), 19 deletions(-)
```

### Evidence
- `tests/test_check_runner.py::TestOnlyExcludesUnconditionalTail::test_only_known_stage_name_excludes_claude_config_drift` (pytest node id, verified passing when recorded)
- `tests/test_check_runner.py::TestOnlyExcludesUnconditionalTail::test_bare_run_still_includes_claude_config_drift` (pytest node id, verified passing when recorded)
- `tests/test_check_runner.py::TestOnlyExcludesUnconditionalTail::test_stage_total_excludes_tail_when_only_is_set` (pytest node id, verified passing when recorded)
